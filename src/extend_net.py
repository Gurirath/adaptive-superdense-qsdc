import numpy as np
import pandas as pd
from deliver import outage_trace
from transports import Link, rates_at
from config import CFG, availability

H = CFG["hybrid"]
S = CFG["scheduling"]
X = CFG["experiments"]


def hybrid_link(L=H["link_km"], demand_frac=H["demand_frac"], buf_s=H["buffer_s"], T=H["duration_s"], seed=H["seed"]):
    lk = Link()
    r = rates_at(L, lk)
    P = r["pair_rate"]
    k = r["key_mode"] / P
    s = r["sdc_two_step"] / P
    A = availability()
    rng = np.random.default_rng(seed)
    up = outage_trace(T, rng)
    d = demand_frac * A * P * k
    cap = buf_s * d
    out = {}
    for strat in ["key_pool", "qsdc_only", "hybrid"]:
        pool, served, keyless, ages, level = cap, 0, 0, [], 0.0
        fifo = [(0, cap)]
        for t in range(T):
            if strat == "qsdc_only":
                if up[t] and P * s >= d:
                    served += 1
                    keyless += 1
                continue
            if up[t]:
                if strat == "hybrid" and P * s >= d:
                    pairs_left = P - d / s
                    served += 1
                    keyless += 1
                    gen = pairs_left * k
                    fifo.append((t, gen))
                    pool = min(cap, pool + gen)
                    level += pool
                    continue
                gen = P * k
                fifo.append((t, gen))
                pool = min(cap, pool + gen)
            if pool >= d:
                pool -= d
                served += 1
                need = d
                while need > 0 and fifo:
                    t0, amt = fifo[0]
                    use = min(amt, need)
                    ages.append((t - t0, use))
                    need -= use
                    if use == amt:
                        fifo.pop(0)
                    else:
                        fifo[0] = (t0, amt - use)
            tot = sum(a for _, a in fifo)
            while tot > cap and fifo:
                t0, amt = fifo[0]
                drop = min(amt, tot - cap)
                tot -= drop
                if drop == amt:
                    fifo.pop(0)
                else:
                    fifo[0] = (t0, amt - drop)
            level += pool
        age = np.average([a for a, _ in ages], weights=[w for _, w in ages]) if ages else 0.0
        out[strat] = dict(on_time=served / T, keyless_frac=keyless / max(served, 1), mean_key_at_rest_s=level / T / d, mean_key_age_s=age)
    max_d_key = A * P * k
    max_d_hyb = A * P * k / ((1 - A) + A * k / s) if s > 0 else 0
    out["capacity_gain_hybrid"] = max_d_hyb / max_d_key
    return out


def schedule_sim(N=S["receivers"], margin=S["margin"], buf_s=S["buffer_s"], sched="equal_up", T=S["duration_s"], seed=S["seed"]):
    rng = np.random.default_rng(seed)
    A = availability()
    d = S["demand_per_receiver"]
    R = margin * N * d / A
    cap = buf_s * d + d
    ups = np.array([outage_trace(T, rng) for _ in range(N)], dtype=bool)
    pools = np.full(N, cap)
    served = 0
    level = 0.0
    for t in range(T):
        u = ups[:, t]
        alloc = np.zeros(N)
        if sched == "static_equal":
            alloc = np.full(N, R / N) * u
        elif sched == "equal_up":
            if u.any():
                alloc[u] = R / u.sum()
        elif sched == "lowest_pool_first":
            budget = R
            idx = np.where(u)[0]
            if len(idx):
                deficit = np.maximum(0, cap - pools[idx])
                order = idx[np.argsort(pools[idx])]
                for i in order:
                    give = min(budget, cap - pools[i])
                    alloc[i] = give
                    budget -= give
                    if budget <= 0:
                        break
        elif sched == "time_to_empty":
            idx = np.where(u)[0]
            if len(idx):
                w = 1.0 / np.maximum(pools[idx], d)
                w = w / w.sum()
                alloc[idx] = np.minimum(R * w, cap - pools[idx])
                spare = R - alloc.sum()
                room = np.where(u, cap - pools - alloc, 0)
                if spare > 0 and room.sum() > 0:
                    alloc += spare * room / room.sum()
        pools = np.minimum(cap, pools + alloc)
        if (pools >= d).all():
            pools -= d
            served += 1
        level += pools.mean()
    return served / T, level / T / d


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    print("== QSDC + pool hybrid on a short link ==")
    for L in X["fig12"]["link_lengths_km"]:
        res = hybrid_link(L=L)
        print(f"L={L}km capacity gain from hybrid = {res.pop('capacity_gain_hybrid'):.3f}")
        print(pd.DataFrame(res).T.round(3).to_string())
    print("== shared-source scheduling for multicast pools ==")
    rows = []
    for margin in CFG["standalone"]["scheduling_margins"]:
        for buf in X["fig16"]["buffers_s"]:
            for s in ["static_equal", "equal_up", "lowest_pool_first", "time_to_empty"]:
                v = [schedule_sim(S["receivers"], margin, buf, s, seed=sd) for sd in range(X["n_seeds"])]
                rows.append(dict(margin=margin, buffer_s=buf, sched=s, on_time=np.mean([a for a, _ in v]), key_at_rest_s=np.mean([b for _, b in v])))
    df = pd.DataFrame(rows)
    df.to_csv("out_scheduling.csv", index=False)
    print(df.pivot_table(index=["margin", "buffer_s"], columns="sched", values="on_time").round(3).to_string())
