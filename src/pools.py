import numpy as np
from deliver import outage_trace


def pool_sim(h, rho, buf_s, T=60000, seed=0, R=1.0, avail=(300.0, 30.0)):
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


def pool_trace(h=4, rho=0.8, buf_s=120, T=3600, seed=3, R=1.0, avail=(300.0, 30.0)):
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
