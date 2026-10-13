import numpy as np
from deliver import outage_trace
from config import CFG

P = CFG["pools"]
PT = P["trace"]
O = CFG["outage"]


def pool_sim(h, rho, buf_s, T=P["duration_s"], seed=P["seed"], R=P["source_rate"], avail=(O["mean_up_s"], O["mean_down_s"])):
    rng = np.random.default_rng(seed)
    A = avail[0] / sum(avail)
    d = rho * A * R
    cap = buf_s * d
    ups = np.array([outage_trace(T, rng, *avail) for _ in range(h)], dtype=float)
    pools = np.full(h, cap)
    served = 0
    for t in range(T):
        pools = np.minimum(cap + d, pools + ups[:, t] * R)
        if (pools >= d).all():
            pools -= d
            served += 1
    return served / T


def pool_trace(h=PT["hops"], rho=PT["load"], buf_s=PT["buffer_s"], T=PT["duration_s"], seed=PT["seed"], R=P["source_rate"], avail=(O["mean_up_s"], O["mean_down_s"])):
    rng = np.random.default_rng(seed)
    A = avail[0] / sum(avail)
    d = rho * A * R
    cap = buf_s * d
    ups = np.array([outage_trace(T, rng, *avail) for _ in range(h)], dtype=bool)
    pools = np.full(h, cap)
    min_level = np.zeros(T)
    served_pool = np.zeros(T, dtype=bool)
    for t in range(T):
        pools = np.minimum(cap + d, pools + ups[:, t] * R)
        if (pools >= d).all():
            pools -= d
            served_pool[t] = True
        min_level[t] = pools.min() / d
    served_jit = ups.all(axis=0)
    return ups, min_level, served_pool, served_jit
