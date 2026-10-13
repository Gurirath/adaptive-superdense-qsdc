import numpy as np
import pandas as pd
from transports import Link, rates_at, eta_fiber


def outage_trace(T, rng, mean_up=300.0, mean_down=30.0):
    up = np.ones(T, dtype=bool)
    t, state = 0, True
    while t < T:
        d = int(max(1, rng.exponential(mean_up if state else mean_down)))
        up[t:t + d] = state
        t += d
        state = not state
    return up


def hop_rate(L, lk):
    return rates_at(L, lk, "tomographic", "direct")["key_mode"]


def swap_rate(hops, L, lk, memory=False):
    eta = eta_fiber(L, lk) * lk.eta_det
    pairs = lk.clock_hz * lk.mu
    key_pp = 0.8
    if not memory:
        return pairs * eta ** hops * (lk.bsm_eff ** (hops - 1)) * key_pp
    link = pairs * eta
    return link * (lk.bsm_eff ** (hops - 1)) * key_pp / (1 + 0.5 * np.log2(max(hops, 1)) * 2)


def simulate_path(hops, strategy, T=100000, L=25.0, demand=256e3, deadline=1, pool_cap=5e8, seed=0, lk=None, paths=3, k_of_n=2, avail=(300.0, 30.0)):
    lk = lk or Link()
    rng = np.random.default_rng(seed)
    R = hop_rate(L, lk)
    n_paths = paths if strategy.startswith("multipath") else 1
    ups = [[outage_trace(T, rng, *avail) for _ in range(hops)] for _ in range(n_paths)]
    path_up = [np.logical_and.reduce(u) if hops > 1 else u[0] for u in ups]
    served = np.zeros(T, dtype=bool)
    if strategy == "jit_trusted_relay":
        served = path_up[0] & (R >= demand)
    elif strategy == "jit_swap_no_memory":
        served = path_up[0] & (swap_rate(hops, L, lk) * deadline >= demand)
    elif strategy == "jit_swap_memory":
        served = path_up[0] & (swap_rate(hops, L, lk, True) * deadline >= demand)
    elif strategy in ("pool_trusted_relay", "pool_end_to_end_swap"):
        if strategy == "pool_trusted_relay":
            pools = np.full(hops, pool_cap / 10)
            gen = np.array(ups[0], dtype=float) * R
            for t in range(T):
                pools = np.minimum(pool_cap, pools + gen[:, t])
                if (pools >= demand).all():
                    pools -= demand
                    served[t] = True
        else:
            pool = pool_cap / 10
            g = swap_rate(hops, L, lk, True)
            for t in range(T):
                if path_up[0][t]:
                    pool = min(pool_cap, pool + g)
                if pool >= demand:
                    pool -= demand
                    served[t] = True
    elif strategy == "multipath_jit_k_of_n":
        cnt = np.sum([p & (R >= demand / k_of_n) for p in path_up], axis=0)
        served = cnt >= k_of_n
    elif strategy == "multipath_pool_k_of_n":
        pools = np.full((n_paths, hops), pool_cap / 10)
        gen = np.array(ups, dtype=float) * R
        share = demand
        for t in range(T):
            pools = np.minimum(pool_cap, pools + gen[:, :, t])
            ok = (pools >= share).all(axis=1)
            if ok.sum() >= k_of_n:
                idx = np.where(ok)[0][:k_of_n]
                pools[idx] -= share
                served[t] = True
    else:
        raise ValueError(strategy)
    return served.mean()


STRATS = ["jit_trusted_relay", "jit_swap_no_memory", "jit_swap_memory", "pool_trusted_relay", "pool_end_to_end_swap", "multipath_jit_k_of_n", "multipath_pool_k_of_n"]
EXPOSURE = {
    "jit_trusted_relay": "h-1 relays see key",
    "jit_swap_no_memory": "no node sees key",
    "jit_swap_memory": "no node sees key",
    "pool_trusted_relay": "h-1 relays see key; key at rest",
    "pool_end_to_end_swap": "no node sees key; key at rest at endpoints only",
    "multipath_jit_k_of_n": "Eve needs relays on 2 of 3 paths",
    "multipath_pool_k_of_n": "Eve needs relays on 2 of 3 paths; key at rest",
}


if __name__ == "__main__":
    lk = Link()
    print("hop rate 25 km:", round(hop_rate(25.0, lk)))
    for h in [1, 2, 4, 8]:
        print("swap no mem", h, swap_rate(h, 25.0, lk), "mem", swap_rate(h, 25.0, lk, True))
    rows = []
    for h in [1, 2, 3, 4, 6, 8, 10]:
        for s in STRATS:
            v = np.mean([simulate_path(h, s, T=40000, seed=sd) for sd in range(2)])
            rows.append({"hops": h, "strategy": s, "on_time": v})
            print(h, s, round(v, 4), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv("out_delivery.csv", index=False)
    print(df.pivot(index="hops", columns="strategy", values="on_time").round(4).to_string())
