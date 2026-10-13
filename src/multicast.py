import numpy as np, pandas as pd
from transports import Link, rates_at, eta_fiber
from deliver import outage_trace
from config import CFG, availability

M = CFG["multicast"]

lk = Link()
L = M["hub_link_km"]
A = availability()
eta = eta_fiber(L, lk) * lk.eta_det
R_bip = rates_at(L, lk, "tomographic", "direct")["key_mode"]
key_frac_ghz = M["key_frac_ghz"]

def ghz_rate(N, deterministic=False):
    if deterministic:
        return M["ghz_deterministic_source_hz"] * eta ** N * lk.eta_det * key_frac_ghz
    pairs_needed = int(np.ceil((N + 1) / 2))
    return M["ghz_spdc_clock_hz"] * (lk.mu ** pairs_needed) * eta ** N * lk.eta_det * key_frac_ghz

def mean_group_rate(N):
    return {"bipartite_links": R_bip * A, "ghz_spdc": ghz_rate(N) * A ** N, "ghz_deterministic": ghz_rate(N, True) * A ** N}

def on_time(N, strategy, demand, buf_s=M["buffer_s"], T=M["duration_s"], seed=M["seed"]):
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
    print(f"R_bip {L:g}km", round(R_bip))
    rows = []
    for N in CFG["standalone"]["multicast_rate_receivers"]:
        r = mean_group_rate(N); r["N"] = N; rows.append(r)
    rt = pd.DataFrame(rows).set_index("N"); print(rt.round(2).to_string())
    rt.to_csv("out_multicast_rate.csv")
    demand = CFG["delivery"]["demand_bps"]
    rows = []
    for N in CFG["experiments"]["fig10"]["receivers"]:
        row = {"N": N}
        for s in ["bipartite_jit", "ghz_jit", "bipartite_pools", "ghz_pool", "bipartite_pools_receiver_fraction"]:
            row[s] = np.mean([on_time(N, s, demand, seed=sd) for sd in range(CFG["experiments"]["n_seeds"])])
        rows.append(row); print(row, flush=True)
    ot = pd.DataFrame(rows).set_index("N"); print(ot.round(4).to_string()); ot.to_csv("out_multicast_ontime.csv")
