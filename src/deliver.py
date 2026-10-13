import numpy as np
import pandas as pd
from transports import Link, rates_at, eta_fiber
from config import CFG

D = CFG["delivery"]
O = CFG["outage"]
X = CFG["experiments"]


def outage_trace(T, rng, mean_up=O["mean_up_s"], mean_down=O["mean_down_s"]):
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
    key_pp = D["key_per_swapped_pair"]
    if not memory:
        return pairs * eta ** hops * (lk.bsm_eff ** (hops - 1)) * key_pp
    link = pairs * eta
    return link * (lk.bsm_eff ** (hops - 1)) * key_pp / (1 + D["swap_memory_coeff"] * np.log2(max(hops, 1)) * D["swap_memory_factor"])


def simulate_path(hops, strategy, T=D["duration_s"], L=D["hop_length_km"], demand=D["demand_bps"], deadline=D["deadline_s"], pool_cap=D["pool_cap_bits"], seed=D["seed"], lk=None, paths=D["paths"], k_of_n=D["k_of_n"], avail=(O["mean_up_s"], O["mean_down_s"])):
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
            pools = np.full(hops, pool_cap / D["pool_initial_divisor"])
            gen = np.array(ups[0], dtype=float) * R
            for t in range(T):
                pools = np.minimum(pool_cap, pools + gen[:, t])
                if (pools >= demand).all():
                    pools -= demand
                    served[t] = True
        else:
            pool = pool_cap / D["pool_initial_divisor"]
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
        pools = np.full((n_paths, hops), pool_cap / D["pool_initial_divisor"])
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


def mean_on_time(hops, strategy, T):
    return np.mean([simulate_path(hops, strategy, T=T, seed=sd) for sd in range(X["n_seeds"])])


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
    print(f"hop rate {D['hop_length_km']:g} km:", round(hop_rate(D["hop_length_km"], lk)))
    for h in CFG["standalone"]["deliver_print_hops"]:
        print("swap no mem", h, swap_rate(h, D["hop_length_km"], lk), "mem", swap_rate(h, D["hop_length_km"], lk, True))
    rows = []
    for h in X["fig07"]["hops"]:
        for s in STRATS:
            v = mean_on_time(h, s, X["fig07"]["duration_s"]["full"])
            rows.append({"hops": h, "strategy": s, "on_time": v})
            print(h, s, round(v, 4), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv("out_delivery.csv", index=False)
    print(df.pivot(index="hops", columns="strategy", values="on_time").round(4).to_string())
