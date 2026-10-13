import numpy as np
import pandas as pd
from dataclasses import dataclass, replace
from core import h2, shannon, werner_weights, key_rate_bbm92, key_rate_tomographic, key_rate_di, finite_key_penalty
from config import CFG

LK = CFG["link"]
TR = CFG["transport"]
NUM = CFG["numerics"]
SA = CFG["standalone"]


@dataclass
class Link:
    alpha_db_km: float = LK["alpha_db_km"]
    eta_det: float = LK["eta_det"]
    p_dark: float = LK["p_dark"]
    e_mis: float = LK["e_mis"]
    clock_hz: float = LK["clock_hz"]
    mu: float = LK["mu"]
    t2_mem_s: float = LK["t2_mem_s"]
    eta_mem: float = LK["eta_mem"]
    t_check_s: float = LK["t_check_s"]
    c_fiber_km_s: float = LK["c_fiber_km_s"]
    bsm_eff: float = LK["bsm_eff"]
    di_herald_hz: float = LK["di_herald_hz"]
    block_bits: float = LK["block_bits"]


def eta_fiber(L, lk):
    return 10 ** (-lk.alpha_db_km * L / 10)


def leg_qber(eta, lk):
    s = lk.mu * eta * lk.eta_det
    n = 2 * lk.p_dark
    return (lk.e_mis * s + 0.5 * n) / (s + n)


def werner_from_qber(Q):
    return werner_weights(max(0.25, 1 - 1.5 * Q))


def depol_from_qber(Q):
    return min(1.0, 2 * Q)


def compose(p, q):
    qv = np.array([1 - 3 * q / 4, q / 4, q / 4, q / 4])
    klein = np.array([[0, 1, 2, 3], [1, 0, 3, 2], [2, 3, 0, 1], [3, 2, 1, 0]])
    out = np.zeros(4)
    for i in range(4):
        for j in range(4):
            out[klein[i, j]] += p[i] * qv[j]
    return out


def worst_entropy_given_qber(ez, ex, grid=NUM["worst_case_grid"]):
    best = 0.0
    lo, hi = 0.0, min(ez, ex)
    for p3 in np.linspace(lo, hi, grid):
        p = np.array([1 - ez - ex + p3, ez - p3, ex - p3, p3])
        if (p < -NUM["weight_tolerance"]).any():
            continue
        best = max(best, shannon(np.clip(p, 0, 1)))
    return best


def eve_bound(p, cert):
    if cert == "tomographic":
        return shannon(p)
    if cert == "bbm92":
        ez, ex = p[1] + p[3], p[2] + p[3]
        return worst_entropy_given_qber(ez, ex)
    return np.nan


def key_per_pair(p, cert):
    if cert == "tomographic":
        return key_rate_tomographic(p)
    if cert == "bbm92":
        return key_rate_bbm92(p)
    if cert == "di":
        V = (4 * p[0] - 1) / 3
        S = 2 * np.sqrt(2) * V
        Q = (1 - V) / 2
        return key_rate_di(S, Q)
    raise ValueError(cert)


def sdc_per_pair(p, q2, cert, bsm="complete"):
    eb = eve_bound(p, cert)
    if np.isnan(eb):
        return np.nan
    if bsm == "complete":
        return max(0.0, 2 - shannon(compose(p, q2)) - eb)
    from core import sdc_linear_optics
    I_ab, _ = sdc_linear_optics(p, q2)
    pw = worst_weights(p, cert)
    _, chi = sdc_linear_optics(pw, 0.0)
    return max(0.0, I_ab - chi)


def worst_weights(p, cert, grid=NUM["worst_case_grid"]):
    if cert == "tomographic":
        return p
    ez, ex = p[1] + p[3], p[2] + p[3]
    best, bp = -1, p
    for p3 in np.linspace(0, min(ez, ex), grid):
        c = np.array([1 - ez - ex + p3, ez - p3, ex - p3, p3])
        if (c < -NUM["weight_tolerance"]).any():
            continue
        c = np.clip(c, 0, 1)
        hc = shannon(c)
        if hc > best:
            best, bp = hc, c
    return bp


def mem_depol(L, lk):
    t = 2 * L / lk.c_fiber_km_s + lk.t_check_s
    return 1 - np.exp(-t / lk.t2_mem_s)


def rates_at(L, lk, cert="tomographic", dist="direct", finite=False, bsm="complete"):
    eta = eta_fiber(L, lk)
    if dist == "direct":
        arrive = lk.clock_hz * lk.mu * eta
        pair_rate = arrive * lk.eta_det ** 2
        Q1 = leg_qber(eta, lk)
    elif dist == "mdi":
        eh = eta_fiber(L / 2, lk) * lk.eta_det
        arrive = lk.clock_hz * lk.mu * eh * eh * lk.bsm_eff
        pair_rate = arrive * lk.eta_det ** 2
        Q1 = min(0.5, 2 * leg_qber(eta_fiber(L / 2, lk), lk))
    elif dist == "di_heralded":
        arrive = lk.di_herald_hz * eta_fiber(L, lk)
        pair_rate = arrive
        Q1 = TR["di_qber"]
    else:
        raise ValueError(dist)
    p = werner_from_qber(Q1)
    pen = finite_key_penalty(lk.block_bits) if finite else 0.0
    kp = max(0.0, key_per_pair(p, cert) - pen)
    out = {"L_km": L, "dist": dist, "cert": cert, "bsm": bsm, "QBER": Q1, "pair_rate": pair_rate}
    out["key_mode"] = pair_rate * kp
    q2 = min(1.0, depol_from_qber(leg_qber(eta, lk)) + mem_depol(L, lk))
    eta2 = eta * lk.eta_mem * lk.eta_det ** 2
    sp = sdc_per_pair(p, q2, cert, bsm)
    out["sdc_two_step"] = np.nan if np.isnan(sp) else arrive * eta2 * max(0.0, sp - 2 * pen)
    out["adaptive"] = np.nanmax([out["key_mode"], out["sdc_two_step"]])
    out["sdc_wins"] = (not np.isnan(sp)) and out["sdc_two_step"] > out["key_mode"]
    rt = (eta * lk.eta_det) ** 2
    Qrt = min(0.5, 2 * leg_qber(eta, lk))
    pp_raw = lk.clock_hz * lk.mu * rt
    out["ping_pong"] = pp_raw * max(0.0, 1 - 2 * h2(Qrt)) if rt > TR["ping_pong_min_round_trip"] else 0.0
    out["dl04"] = lk.clock_hz * lk.mu * rt * max(0.0, 1 - 2 * h2(Qrt)) if dist == "direct" else np.nan
    return out


def sweep(lk=None, dists=("direct", "mdi", "di_heralded"), certs=("bbm92", "tomographic", "di"), Ls=None, finite=False):
    lk = lk or Link()
    Ls = np.arange(*TR["distance_grid_km"]) if Ls is None else Ls
    rows = []
    for d in dists:
        for c in certs:
            if c == "di" and d != "di_heralded":
                continue
            if d == "di_heralded" and c != "di":
                continue
            for L in Ls:
                rows.append(rates_at(float(L), lk, c, d, finite))
    return pd.DataFrame(rows)


def switch_threshold_eta(p, q2, cert="tomographic"):
    k = key_per_pair(p, cert)
    s = sdc_per_pair(p, q2, cert)
    if s <= 0:
        return np.inf
    return k / s


if __name__ == "__main__":
    lk = Link()
    df = sweep(lk)
    df.to_csv("out_transports.csv", index=False)
    d = df[(df.dist == "direct") & (df.cert == "tomographic")]
    for L in SA["transports_print_km"]:
        r = d[d.L_km == L].iloc[0]
        print(f"L={L:3d} Q={r.QBER:.4f} key={r.key_mode:10.1f} sdc={r.sdc_two_step:10.1f} adapt={r.adaptive:10.1f} pp={r.ping_pong:8.1f} dl04={r.dl04:10.1f}")
    cross = d[~d.sdc_wins].L_km.min()
    print("crossover km (tomographic, direct):", cross)
    db = df[(df.dist == "direct") & (df.cert == "bbm92")]
    print("crossover km (bbm92, direct):", db[~db.sdc_wins].L_km.min())
    for F in SA["transports_fidelities"]:
        p = werner_weights(F)
        print(F, "eta* tomo", round(switch_threshold_eta(p, 0.0), 4), "eta* bbm92", round(switch_threshold_eta(p, 0.0, "bbm92"), 4), "eta* q=.02", round(switch_threshold_eta(p, CFG["experiments"]["fig03"]["report_return_noise"]), 4))
    for name, sub in df.groupby(["dist", "cert"]):
        mx = sub[sub.adaptive > SA["transports_min_rate"]].L_km.max()
        print(name, "max distance with >1 bit/s adaptive:", mx, " key-only:", sub[sub.key_mode > SA["transports_min_rate"]].L_km.max())
    dfin = sweep(lk, finite=True)
    dfin.to_csv("out_transports_finite.csv", index=False)
