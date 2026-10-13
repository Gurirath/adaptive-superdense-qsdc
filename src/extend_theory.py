import numpy as np
from core import h2, shannon
from transports import Link, rates_at, leg_qber, eta_fiber


def finite_key_rate(n, Q, eps=1e-10, f_ec=1.16, pe_frac=0.1):
    if n < 1e3:
        return 0.0
    n_pe = pe_frac * n
    n_key = n - n_pe
    delta = np.sqrt(np.log(1 / eps) / (2 * n_pe))
    Qu = min(0.5, Q + delta)
    r = n_key * (1 - h2(Qu) - f_ec * h2(Q)) - 2 * np.log2(1 / eps) - 7 * np.sqrt(n_key * np.log2(2 / eps))
    return max(0.0, r / n)


def pool_vs_jit_blocks(lk=None, deadline_s=1.0, pool_block=1e10):
    lk = lk or Link()
    rows = []
    for L in [10, 50, 100, 150, 200, 250]:
        eta = eta_fiber(L, lk)
        pairs_s = lk.clock_hz * lk.mu * eta * lk.eta_det ** 2
        Q = leg_qber(eta, lk)
        n_jit = pairs_s * deadline_s
        r_jit = finite_key_rate(n_jit, Q) * pairs_s
        r_pool = finite_key_rate(min(pool_block, pairs_s * 3600), Q) * pairs_s
        r_asym = max(0.0, 1 - h2(Q) - 1.16 * h2(Q)) * pairs_s
        rows.append((L, pairs_s, Q, n_jit, r_jit, r_pool, r_asym))
    return rows


def switch_threshold_qudit(d, F):
    p0 = F
    rest = (1 - F) / (d * d - 1)
    p = np.array([p0] + [rest] * (d * d - 1))
    H = shannon(p)
    key = max(0.0, np.log2(d) - H)
    sdc = max(0.0, 2 * np.log2(d) - 2 * H)
    return key / sdc if sdc > 0 else np.inf, key, sdc


def two_way_detector_floor(eta_needed=0.75):
    return np.sqrt(eta_needed)


if __name__ == "__main__":
    print("== pool unlocks large finite-key blocks (1 s deadline JIT vs pooled 1 h blocks) ==")
    for L, ps, Q, nj, rj, rp, ra in pool_vs_jit_blocks():
        print(f"L={L:3d}km pairs/s={ps:10.1f} Q={Q:.4f} n_jit={nj:10.0f} jit={rj:10.1f} pool={rp:10.1f} asym={ra:10.1f} gain={'inf' if rj == 0 and rp > 0 else (rp / rj if rj > 0 else float('nan')):}")
    print("== switch threshold vs dimension ==")
    for d in [2, 3, 4, 8, 16]:
        for F in [0.99, 0.95, 0.9]:
            t, k, s = switch_threshold_qudit(d, F)
            print(f"d={d:2d} F={F} eta*={t:.3f} key/pair={k:.3f} sdc/pair={s:.3f}")
    print("== two-way protocol detector floor ==")
    for thr in [0.6, 0.75]:
        print(f"round-trip bound {thr} -> per-pass detector+device efficiency must exceed {two_way_detector_floor(thr):.3f}")
