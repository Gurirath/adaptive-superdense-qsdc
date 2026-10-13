import numpy as np, pandas as pd
from transports import Link, rates_at, eta_fiber
from deliver import outage_trace

lk = Link()
L = 20.0
A = 300/330
eta = eta_fiber(L, lk) * lk.eta_det
R_bip = rates_at(L, lk, "tomographic", "direct")["key_mode"]
key_frac_ghz = 0.8

def ghz_rate(N, deterministic=False):
    if deterministic:
        return 1e8 * eta ** N * lk.eta_det * key_frac_ghz
    pairs_needed = int(np.ceil((N + 1) / 2))
    return 1e9 * (lk.mu ** pairs_needed) * eta ** N * lk.eta_det * key_frac_ghz

def mean_group_rate(N):
    return {"bipartite_links": R_bip * A, "ghz_spdc": ghz_rate(N) * A ** N, "ghz_deterministic": ghz_rate(N, True) * A ** N}

def on_time(N, strategy, demand, buf_s=120, T=30000, seed=0):
    rng = np.random.default_rng(seed)
    ups = np.array([outage_trace(T, rng) for _ in range(N)], dtype=bool)
    all_up = ups.all(axis=0)
    if strategy == "bipartite_jit":
        return float((all_up & (R_bip >= demand)).mean())
    if strategy == "ghz_jit":
        return float((all_up & (ghz_rate(N, True) >= demand)).mean())
    if strategy == "bipartite_pools":
        cap = buf_s * demand + demand
        pools = np.full(N, cap); served = 0
        for t in range(T):
            pools = np.minimum(cap, pools + ups[:, t] * R_bip)
            if (pools >= demand).all():
                pools -= demand; served += 1
        return served / T
    if strategy == "ghz_pool":
        cap = buf_s * demand + demand
        pool = cap; served = 0; g = ghz_rate(N, True)
        for t in range(T):
            if all_up[t]: pool = min(cap, pool + g)
            if pool >= demand:
                pool -= demand; served += 1
        return served / T
    if strategy == "bipartite_pools_receiver_fraction":
        cap = buf_s * demand + demand
        pools = np.full(N, cap); frac = 0.0
        for t in range(T):
            pools = np.minimum(cap, pools + ups[:, t] * R_bip)
            ok = pools >= demand
            pools[ok] -= demand
            frac += ok.mean()
        return frac / T

if __name__ == "__main__":
    print("R_bip 20km", round(R_bip))
    rows = []
    for N in [2, 3, 4, 6, 8, 12, 16, 24, 32]:
        r = mean_group_rate(N); r["N"] = N; rows.append(r)
    rt = pd.DataFrame(rows).set_index("N"); print(rt.round(2).to_string())
    rt.to_csv("out_multicast_rate.csv")
    demand = 256e3
    rows = []
    for N in [2, 4, 8, 16, 32]:
        row = {"N": N}
        for s in ["bipartite_jit", "ghz_jit", "bipartite_pools", "ghz_pool", "bipartite_pools_receiver_fraction"]:
            row[s] = np.mean([on_time(N, s, demand, seed=sd) for sd in range(2)])
        rows.append(row); print(row, flush=True)
    ot = pd.DataFrame(rows).set_index("N"); print(ot.round(4).to_string()); ot.to_csv("out_multicast_ontime.csv")
