import os
import json
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core import werner_weights, shannon, sdc_information, sdc_linear_optics, chsh_from_weights
from transports import Link, rates_at, sweep as transport_sweep, switch_threshold_eta, eta_fiber
from detect import telemetry, features, static_threshold, multi_threshold, run as detect_run, ATTACKS
from deliver import simulate_path, outage_trace, STRATS
from pools import pool_sim, pool_trace
from multicast import mean_group_rate, on_time as mc_on_time, ghz_rate
from extend_net import hybrid_link, schedule_sim
from extend_theory import pool_vs_jit_blocks, switch_threshold_qudit
from config import CFG, availability

X = CFG["experiments"]

INK = "#111111"
G1 = "#555555"
G2 = "#8a8a8a"
G3 = "#bdbdbd"
ACC = "#c0392b"
SHADE = "#e9e9e9"

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "axes.titleweight": "bold",
    "axes.titlesize": 11.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e4e4e4",
    "grid.linewidth": 0.6,
    "xtick.color": INK,
    "ytick.color": INK,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "lines.linewidth": 1.8,
    "axes.axisbelow": True,
})


class Ctx:
    def __init__(self, out_dir, fast):
        self.out = out_dir
        self.fast = fast
        self.mode = "fast" if fast else "full"
        self.results = {}
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, "data"), exist_ok=True)

    def save(self, fig, name, caption):
        path = os.path.join(self.out, name)
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        self.results.setdefault("figures", []).append({"file": name, "caption": caption})
        print(f"  saved {name}")


def fig01_rate_vs_distance(c):
    lk = Link()
    df = transport_sweep(lk, dists=("direct",), certs=("tomographic",), Ls=np.arange(*CFG["transport"]["distance_grid_km"]))
    df.to_csv(os.path.join(c.out, "data", "rates_vs_distance.csv"), index=False)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.semilogy(df.L_km, df.adaptive, color=ACC, lw=5, alpha=0.3, label="Adaptive switch (proposed): best of both")
    ax.semilogy(df.L_km, df.key_mode, color=INK, label="Key mode (entanglement QKD + one-time pad)")
    ax.semilogy(df.L_km, df.sdc_two_step.clip(lower=1e-1), color=G2, ls="--", label="Superdense direct (two-step QSDC)")
    ax.semilogy(df.L_km, df.dl04.clip(lower=1e-1), color=G2, ls=":", label="DL04 single-photon QSDC")
    cross = float(df[~df.sdc_wins].L_km.min())
    ax.axvline(cross, color=ACC, lw=0.8, ls="-.")
    ax.annotate(f"switch point ≈ {cross:.0f} km\n(superdense wins left of here)", xy=(cross, 4.6e6), xytext=(35, 9e6), color=ACC, fontsize=8.5, arrowprops=dict(arrowstyle="->", color=ACC, lw=0.8))
    ax.text(150, 3e5, "Ping-pong: 0 secure bits/s\nat every distance", color=G1, fontsize=8.5)
    ax.set_ylim(1e0, 2e7)
    ax.set_xlabel("Fiber distance (km)")
    ax.set_ylabel("Secure bits per second (log)")
    ax.set_title("1-to-1: secure rate vs distance for each transport")
    ax.legend(loc="lower left")
    c.results["switch_point_km"] = cross
    for L in X["fig01"]["report_distances_km"]:
        c.results[f"rate_at_{L}km"] = {k: float(df[df.L_km == L][k].iloc[0]) for k in ["key_mode", "sdc_two_step", "adaptive", "dl04"]}
    c.save(fig, "fig01_rate_vs_distance.png", "Secure rate vs distance; superdense direct only wins below the switch point; ping-pong never secure")


def fig02_superdense_security(c):
    Fs = np.linspace(*X["fig02"]["fidelity_grid"])
    rows = []
    for F in Fs:
        p = werner_weights(F)
        r = sdc_information(p, 0.0)
        Il, chil = sdc_linear_optics(p)
        rows.append(dict(F=F, eve=r["chi_eve_intercept"], bob=r["I_bob"], sdc=max(0, 2 - 2 * shannon(p)), key=max(0, 1 - shannon(p)), sdc_lin=max(0, Il - chil), S=chsh_from_weights(p)))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(c.out, "data", "superdense_security.csv"), index=False)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(d.F, d.sdc, color=ACC, label="Superdense direct: secure bits per pair = 2 − 2H(p)")
    ax.plot(d.F, d.key, color=INK, label="Key mode: secure bits per pair = 1 − H(p)")
    ax.plot(d.F, d.sdc_lin, color=G2, ls="--", label="Superdense with linear-optics Bell measurement")
    ax.plot(d.F, d.eve, color=G1, ls=":", label="Eve's max info even if she grabs the encoded qubit = H(p)")
    ax.set_xlabel("Verified pair fidelity F")
    ax.set_ylabel("Bits per entangled pair")
    ax.set_title("Superdense coding: 2× secure bits per pair, Eve capped at H(p)")
    ax2 = ax.secondary_xaxis("top", functions=(lambda F: 2 * np.sqrt(2) * (4 * F - 1) / 3, lambda S: (3 * S / (2 * np.sqrt(2)) + 1) / 4))
    ax2.set_xlabel("Equivalent CHSH value S", fontsize=9)
    ax.legend(loc="upper left", fontsize=8.5)
    p95 = werner_weights(X["fig02"]["report_fidelity"])
    c.results["F095"] = {"eve_bits": shannon(p95), "sdc_secure": 2 - 2 * shannon(p95), "key_secure": 1 - shannon(p95)}
    c.save(fig, "fig02_superdense_security.png", "Density-matrix result: superdense gives exactly 2x key mode per verified pair; Eve's information bounded by pair entropy H(p)")


def fig03_switch_rule(c):
    xc = X["fig03"]
    etas = np.linspace(*xc["eta_grid"])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    styles = list(zip(xc["fidelities"], [INK, G1, G2], ["-", "--", ":"]))
    for F, col, ls in styles:
        p = werner_weights(F)
        k = 1 - shannon(p)
        s = 2 - 2 * shannon(p)
        ax.plot(etas, etas * s / k, color=col, ls=ls, label=f"F = {F} (all fidelities overlap)")
    pn = werner_weights(xc["noisy_fidelity"])
    from transports import sdc_per_pair
    sn = sdc_per_pair(pn, xc["noisy_return_noise"], "tomographic")
    ax.plot(etas, etas * sn / (1 - shannon(pn)), color=G2, lw=1.2, ls="-.", label=f"F = {xc['noisy_fidelity']} with {xc['noisy_return_noise'] * 100:.0f}% noise on return leg")
    ax.axhline(1, color=INK, lw=0.8)
    ax.axvline(0.5, color=ACC, lw=1.2)
    ax.fill_betweenx([0, 2.1], 0.5, 1.0, color=ACC, alpha=0.07)
    ax.text(0.53, 1.75, "use superdense direct", color=ACC)
    ax.text(0.12, 1.75, "use key mode", color=INK)
    ax.text(0.485, 1.06, "η* = 0.5", color=ACC, ha="right")
    ax.set_ylim(0, 2.1)
    ax.set_xlabel("Return-leg transmission η (fraction of encoded photons that arrive)")
    ax.set_ylabel("Superdense rate ÷ key-mode rate")
    ax.set_title("Switching rule: superdense wins only when η > 1/2")
    ax.legend(loc="lower right")
    dims = xc["dimensions"]
    c.results["switch_threshold_by_dimension"] = {str(d): switch_threshold_qudit(d, xc["report_fidelity"])[0] for d in dims}
    c.results["switch_threshold_with_2pct_return_noise"] = float(switch_threshold_eta(werner_weights(xc["report_fidelity"]), xc["report_return_noise"]))
    c.save(fig, "fig03_switch_rule.png", "Closed-form switching rule eta* = (1-H)/(2-H(p.q)-H) = 1/2 for any fidelity and any qudit dimension")


def fig04_crossover_sensitivity(c):
    xc = X["fig04"]
    Ls = np.arange(*xc["distance_grid_km"])
    labels, vals = [], []
    for T2 in xc["t2_values_s"]:
        lk = Link(t2_mem_s=T2)
        d = pd.DataFrame([rates_at(float(L), lk) for L in Ls])
        labels.append(f"memory\nT2={T2:g}s")
        vals.append(float(d[~d.sdc_wins].L_km.min()))
    lk = Link(t2_mem_s=xc["perfect_t2_s"], eta_mem=xc["perfect_eta_mem"])
    d = pd.DataFrame([rates_at(float(L), lk) for L in Ls])
    labels.append("perfect\nmemory")
    vals.append(float(d[~d.sdc_wins].L_km.min()))
    d = pd.DataFrame([rates_at(float(L), Link(), "tomographic", "direct", False, "linear") for L in Ls])
    labels.append("linear-optics\nBell meas.")
    vals.append(float(d[~d.sdc_wins].L_km.min()))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    cols = [G3, G2, G1, INK, ACC, G3]
    ax.bar(labels, vals, color=cols, edgecolor=INK, linewidth=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.3, f"{v:.0f} km", ha="center")
    ax.set_ylabel("Max distance where superdense wins (km)")
    ax.set_title("Superdense coding is a short-link tool: crossover distance")
    c.results["crossover_km"] = dict(zip([l.replace("\n", " ") for l in labels], vals))
    c.save(fig, "fig04_crossover_sensitivity.png", "Where superdense direct beats key mode, by memory quality; linear-optics Bell measurement never wins")


def fig05_06_detection(c):
    xc = X["fig05"]
    fa = CFG["detection"]["false_alarm"]
    seeds_train = tuple(xc["train_seeds"][c.mode])
    res, clf, thr = detect_run(seeds_train=seeds_train, seeds_test=tuple(xc["test_seeds"]))
    train = pd.concat([telemetry(seed=s) for s in seeds_train], ignore_index=True)
    te = telemetry(T=xc["display_duration_s"], seed=xc["display_seed"])
    F = features(te)
    ml = (1 - clf.predict_proba(F)[:, 0]) > thr
    st = static_threshold(te, fa, train).values.astype(bool)
    mm = multi_threshold(te, fa, train).values.astype(bool)
    lab = te.label.values
    starts = np.where(np.diff(np.r_[0, (lab > 0).astype(int)]) == 1)[0]
    best, w = 0, xc["window_s"]
    for s0 in range(0, xc["display_duration_s"] - w, xc["window_step_s"]):
        seg = lab[s0:s0 + w]
        n = len(set(seg[seg > 0]))
        if n > best:
            best, start = n, s0
        if n == len(ATTACKS) - 1:
            break
    sl = slice(start, start + w)
    t = np.arange(w) / 60.0
    seg = te.iloc[sl]
    fig, axs = plt.subplots(5, 1, figsize=(9, 8.2), sharex=True, gridspec_kw=dict(height_ratios=[1.3, 1, 1, 0.45, 0.45]))
    names = {1: "intercept-resend", 2: "detector blinding", 3: "Trojan horse"}
    labseg = lab[sl]
    nlab = 0
    for ax in axs[:3]:
        i = 0
        while i < w:
            if labseg[i] > 0:
                j = i
                while j < w and labseg[j] == labseg[i]:
                    j += 1
                ax.axvspan(t[i], t[min(j, w - 1)], color=ACC, alpha=0.13, lw=0)
                if ax is axs[0]:
                    ax.text((t[i] + t[min(j, w - 1)]) / 2, 1.02 + 0.11 * (nlab % 2), names[labseg[i]], transform=ax.get_xaxis_transform(), fontsize=7.5, color=ACC, va="bottom", ha="center")
                    nlab += 1
                i = j
            else:
                i += 1
    axs[0].plot(t, (seg.qz + seg.qx) * 100, color=INK, lw=0.6)
    axs[0].axhline(np.quantile((train.qz + train.qx)[train.label == 0], 1 - fa) * 100, color=G2, ls="--", lw=1)
    axs[0].set_ylabel("QBER sum (%)")
    fig.suptitle("Time series: link telemetry with attacks (shaded red) and detector alarms", fontweight="bold", y=0.985)
    fig.subplots_adjust(top=0.9, hspace=0.28)
    axs[1].plot(t, seg.dark, color=G1, lw=0.6)
    axs[1].set_ylabel("Dark counts / s")
    axs[2].plot(t, seg.backrefl, color=G1, lw=0.6)
    axs[2].set_ylabel("Back-reflection")
    benign = labseg == 0
    fa_st = st[sl][benign].mean() * 100
    fa_ml = ml[sl][benign].mean() * 100
    for ax, flags, name in [(axs[3], st[sl], f"Static QBER alarm\n(false alarms {fa_st:.1f}%)"), (axs[4], ml[sl], f"ML alarm\n(false alarms {fa_ml:.1f}%)")]:
        ax.vlines(t[flags], 0, 1, color=INK if name.startswith("Static") else ACC, lw=0.6)
        ax.set_yticks([])
        ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=8.5)
        ax.grid(False)
    axs[4].set_xlabel("Time (minutes)")
    c.save(fig, "fig05_attack_timeseries.png", "Time series of QBER, dark counts and back-reflection with three attack types; static threshold misses blinding and Trojan attacks, ML catches them")
    res.to_csv(os.path.join(c.out, "data", "detection_metrics.csv"))
    rows = ["static_qber_threshold", "multi_monitor_thresholds", "ml_gradient_boosting"]
    cols = ["intercept_resend_recall", "detector_blinding_recall", "trojan_horse_recall", "overall_recall"]
    fig, ax = plt.subplots(figsize=(7.6, 4))
    x = np.arange(len(cols))
    wdt = 0.26
    pretty = {"static_qber_threshold": "Static QBER threshold (standard)", "multi_monitor_thresholds": "Thresholds on 4 monitors", "ml_gradient_boosting": "ML, gradient boosting (proposed)"}
    for i, (r, col) in enumerate(zip(rows, [G3, G1, ACC])):
        vals = res.loc[r, cols].astype(float).values * 100
        ax.bar(x + (i - 1) * wdt, vals, wdt, color=col, edgecolor=INK, linewidth=0.5, label=pretty[r])
        for xi, v in zip(x + (i - 1) * wdt, vals):
            ax.text(xi, v + 1.5, f"{v:.0f}", ha="center", fontsize=7.5)
    ax.set_xticks(x, ["intercept-resend", "detector blinding", "Trojan horse", "overall"])
    ax.set_ylabel("Attack windows caught (%) at 1% false alarms")
    ax.set_ylim(0, 112)
    ax.set_title("Attack detection: ML vs standard checks")
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    c.results["detection"] = res.loc[rows, cols + ["false_alarm"]].astype(float).round(3).to_dict(orient="index")
    c.save(fig, "fig06_detection_comparison.png", "Recall per attack type at a 1% false-alarm budget (synthetic telemetry, modelled signatures)")


def fig07_on_time_vs_hops(c):
    xc = X["fig07"]
    T = xc["duration_s"][c.mode]
    hops = xc["hops"]
    rows = []
    for h in hops:
        for s in STRATS:
            rows.append(dict(hops=h, strategy=s, on_time=np.mean([simulate_path(h, s, T=T, seed=sd) for sd in range(X["n_seeds"])])))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(c.out, "data", "on_time_vs_hops.csv"), index=False)
    piv = df.pivot(index="hops", columns="strategy", values="on_time")
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    spec = {
        "jit_trusted_relay": (INK, "-", "o", "Just-in-time, trusted relays"),
        "jit_swap_no_memory": (G2, ":", "x", "Entanglement swapping, no memory"),
        "multipath_jit_k_of_n": (G1, "--", "s", "Multipath 2-of-3, no pools"),
        "pool_end_to_end_swap": (G2, "-.", "^", "End-to-end swapping + pool"),
        "pool_trusted_relay": (ACC, "-", "D", "Key pool at every hop (proposed)"),
        "multipath_pool_k_of_n": (ACC, "--", "v", "Pools + multipath 2-of-3 (proposed)"),
    }
    for k, (col, ls, mk, lab) in spec.items():
        ax.plot(piv.index, piv[k] * 100, color=col, ls=ls, marker=mk, ms=5, label=lab)
    ax.plot(piv.index, availability() ** piv.index * 100, color=INK, lw=0.6, alpha=0.5)
    ax.text(6.2, availability() ** 6 * 100 - 9, "theory: 0.909^hops", fontsize=8, color=G1, bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1.5))
    ax.set_xlabel("Number of hops")
    ax.set_ylabel("Keys delivered on time (%)")
    ax.set_ylim(-3, 105)
    ax.set_title("The 'key arrives late' problem and the fix")
    ax.legend(loc="lower left", fontsize=8)
    c.results["on_time_vs_hops"] = {s: {int(h): round(float(v), 4) for h, v in piv[s].items()} for s in piv.columns}
    c.save(fig, "fig07_on_time_vs_hops.png", "On-time key delivery collapses as 0.909^hops without buffering; per-hop key pools hold ~100% (supply 10x demand here; fig09 tests tight load)")


def fig08_pool_timeseries(c):
    xc = X["fig08"]
    ups, lvl, sp, sj = pool_trace(h=xc["hops"], rho=xc["load"], buf_s=xc["buffer_s"], T=xc["duration_s"], seed=xc["seed"])
    t = np.arange(len(lvl)) / 60
    fig, axs = plt.subplots(3, 1, figsize=(9, 6), sharex=True, gridspec_kw=dict(height_ratios=[1, 1.4, 0.8]))
    for i in range(ups.shape[0]):
        down = ~ups[i]
        axs[0].fill_between(t, i, i + 0.8, where=down, color=ACC, step="post", lw=0)
        axs[0].fill_between(t, i, i + 0.8, where=~down, color=G3, step="post", lw=0)
    axs[0].set_yticks(np.arange(ups.shape[0]) + 0.4, [f"hop {i+1}" for i in range(ups.shape[0])])
    axs[0].set_title("Time series: 4-hop path with outages (red) and the lowest key pool level")
    axs[0].grid(False)
    axs[1].plot(t, lvl, color=INK, lw=1)
    axs[1].fill_between(t, 0, lvl, color=SHADE)
    axs[1].set_ylabel("Lowest pool\n(seconds of demand)")
    axs[2].vlines(t[~sj], 1, 1.8, color=G1, lw=0.5)
    axs[2].vlines(t[~sp], 0, 0.8, color=ACC, lw=0.8)
    axs[2].set_yticks([0.4, 1.4], [f"pool misses ({(~sp).mean()*100:.1f}%)", f"just-in-time misses ({(~sj).mean()*100:.1f}%)"])
    axs[2].grid(False)
    axs[2].set_xlabel("Time (minutes)")
    c.results["pool_timeseries_misses"] = {"jit": float((~sj).mean()), "pool": float((~sp).mean())}
    c.save(fig, "fig08_pool_timeseries.png", "Pools drain during outages and refill after, so requests keep being served while just-in-time delivery fails whenever any hop is down")


def fig09_pool_sizing(c):
    xc = X["fig09"]
    T = xc["duration_s"][c.mode]
    bufs = xc["buffers_s"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    rows = []
    for h, col, mk in zip(xc["hops"], [G2, G1, INK], ["o", "s", "D"]):
        for rho, ls in zip(xc["loads"], ["-", "--"]):
            v = [pool_sim(h, rho, b, T=T, seed=xc["seed"]) for b in bufs]
            rows += [dict(hops=h, rho=rho, buffer_s=b, on_time=x) for b, x in zip(bufs, v)]
            ax.plot(np.array(bufs) / CFG["outage"]["mean_down_s"], np.array(v) * 100, color=col, ls=ls, marker=mk, ms=4, label=f"{h} hop{'s' if h > 1 else ''}, {int(rho*100)}% load")
    pd.DataFrame(rows).to_csv(os.path.join(c.out, "data", "pool_sizing.csv"), index=False)
    ax.axvline(4, color=ACC, lw=1)
    ax.text(4.15, 58, "sizing rule:\npool ≈ 4× mean outage", color=ACC, fontsize=8.5)
    ax.set_xlabel("Pool size (multiples of mean outage length)")
    ax.set_ylabel("On-time (%)")
    ax.set_title("How big should the key pool be?")
    ax.legend(fontsize=7.5, ncol=1, loc="center right", bbox_to_anchor=(1.0, 0.42))
    c.save(fig, "fig09_pool_sizing.png", "Pool size needed for on-time delivery: about 4x the mean outage reaches 94-98% even at 8 hops and 95% load")


def fig10_11_multicast(c):
    xc = X["fig10"]
    T = xc["duration_s"][c.mode]
    Ns = xc["receivers"]
    strats = {"bipartite_jit": (INK, "-", "o", "Bipartite links, just-in-time"), "ghz_jit": (G2, ":", "x", "GHZ conference key"), "bipartite_pools": (ACC, "-", "D", "Per-receiver pools (proposed)"), "bipartite_pools_receiver_fraction": (ACC, "--", "v", "Pools: share of receivers on time")}
    rows = []
    for N in Ns:
        r = {"N": N}
        for s in strats:
            r[s] = np.mean([mc_on_time(N, s, CFG["delivery"]["demand_bps"], T=T, seed=sd) for sd in range(X["n_seeds"])])
        rows.append(r)
    df = pd.DataFrame(rows).set_index("N")
    df.to_csv(os.path.join(c.out, "data", "multicast_on_time.csv"))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for s, (col, ls, mk, lab) in strats.items():
        ax.plot(df.index, df[s] * 100, color=col, ls=ls, marker=mk, label=lab)
    ax.set_xscale("log", base=2)
    ax.set_xticks(Ns, [str(n) for n in Ns])
    ax.set_xlabel("Number of receivers N")
    ax.set_ylabel("Group key on time (%)")
    ax.set_ylim(-3, 105)
    ax.set_title("1-to-N multicast: who gets the group key on time")
    ax.legend(loc="center left", fontsize=8)
    c.results["multicast_on_time"] = df.round(4).to_dict()
    c.save(fig, "fig10_multicast_on_time.png", "Multicast: just-in-time falls as 0.909^N; GHZ dies past N=4; per-receiver pools stay at 94-99%")
    lk = Link()
    src = lk.clock_hz * lk.mu
    xc = X["fig11"]
    locs = xc["hub_links_km"]
    Nn = xc["receivers"]
    grid = np.zeros((len(locs), len(Nn)))
    Rb = rates_at(xc["bottleneck_km"], lk)["key_mode"]
    eb = eta_fiber(xc["bottleneck_km"], lk) * lk.eta_det
    for i, Ll in enumerate(locs):
        el = eta_fiber(Ll, lk) * lk.eta_det
        for j, N in enumerate(Nn):
            grid[i, j] = src * eb * el ** N * lk.eta_det * CFG["multicast"]["key_frac_ghz"] / (Rb / N)
    fig, ax = plt.subplots(figsize=(7.2, 4))
    im = ax.imshow(np.log2(grid), cmap="RdGy_r", vmin=-4, vmax=4, aspect="auto", origin="lower")
    for i in range(len(locs)):
        for j in range(len(Nn)):
            ax.text(j, i, f"{grid[i,j]:.2f}", ha="center", va="center", fontsize=7.5, color="white" if abs(np.log2(grid[i, j])) > 2.5 else INK)
    ax.set_xticks(range(len(Nn)), Nn)
    ax.set_yticks(range(len(locs)), locs)
    ax.set_xlabel("Number of receivers N")
    ax.set_ylabel("Hub-to-receiver link (km)")
    ax.set_title(f"GHZ ÷ bipartite group-key rate ({xc['bottleneck_km']:g} km bottleneck)")
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("log2 ratio (red = GHZ better)")
    c.save(fig, "fig11_ghz_vs_bipartite.png", "GHZ conference keys only beat bipartite keys (max ~1.8x) behind a bottleneck with receivers within ~2 km and N<=8")


def fig12_hybrid(c):
    xc = X["fig12"]
    T = xc["duration_s"][c.mode]
    res = {L: hybrid_link(L=L, T=T) for L in xc["link_lengths_km"]}
    r1 = res[xc["report_link_km"]]
    gain = {L: r.pop("capacity_gain_hybrid") for L, r in res.items()}
    tab = pd.DataFrame(r1).T
    tab.to_csv(os.path.join(c.out, "data", "hybrid_1km.csv"))
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.6))
    order = ["key_pool", "qsdc_only", "hybrid"]
    names = ["Key + pool", "QSDC only", "Hybrid\n(proposed)"]
    cols = [G2, G3, ACC]
    for ax, metric, ttl, scale in [(axs[0], "on_time", "On-time (%)", 100), (axs[1], "keyless_frac", "Traffic never touching\na stored key (%)", 100), (axs[2], "mean_key_age_s", "Avg age of stored key\nwhen used (s)", 1)]:
        vals = [tab.loc[o, metric] * scale for o in order]
        ax.bar(names, vals, color=cols, edgecolor=INK, linewidth=0.5)
        for i, v in enumerate(vals):
            ax.text(i, v * 1.01 + (1 if scale == 100 else 3), f"{v:.1f}" if scale == 100 else f"{v:.0f}", ha="center", fontsize=8.5)
        ax.set_title(ttl, fontsize=10)
        ax.tick_params(axis="x", labelsize=8.5)
    axs[0].set_ylim(80, 103)
    fig.suptitle("QSDC + key-pool hybrid on a 1 km link: reliability of pools, exposure of QSDC", fontweight="bold", y=1.04)
    c.results["hybrid_1km"] = tab.round(3).to_dict(orient="index")
    c.results["hybrid_capacity_gain"] = {str(k): round(v, 3) for k, v in gain.items()}
    c.save(fig, "fig12_hybrid_bars.png", "Hybrid keeps 99.6% on-time like pools while 92% of traffic is sent keyless; trade-off: stored keys age longer")
    xc = X["fig13"]
    hy = CFG["hybrid"]
    lk = Link()
    r = rates_at(xc["link_km"], lk)
    P, k, s = r["pair_rate"], r["key_mode"] / r["pair_rate"], r["sdc_two_step"] / r["pair_rate"]
    A = availability()
    Tn = xc["duration_s"]
    up = outage_trace(Tn, np.random.default_rng(xc["seed"]))
    d = hy["demand_frac"] * A * P * k
    cap = hy["buffer_s"] * d
    pool = cap
    mode = np.zeros(Tn, dtype=int)
    lvl = np.zeros(Tn)
    for t in range(Tn):
        if up[t]:
            mode[t] = 1
            pool = min(cap, pool + (P - d / s) * k)
        elif pool >= d:
            pool -= d
            mode[t] = 2
        lvl[t] = pool / d
    tt = np.arange(Tn) / 60
    fig, axs = plt.subplots(2, 1, figsize=(9, 4.6), sharex=True, gridspec_kw=dict(height_ratios=[0.6, 1.4]))
    axs[0].fill_between(tt, 0, 1, where=mode == 1, color=G3, step="post", lw=0, label="QSDC direct (no key)")
    axs[0].fill_between(tt, 0, 1, where=mode == 2, color=ACC, step="post", lw=0, label="Outage: one-time pad from pool")
    axs[0].fill_between(tt, 0, 1, where=mode == 0, color=INK, step="post", lw=0, label="Missed")
    axs[0].set_yticks([])
    axs[0].grid(False)
    fig.legend(loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=8.5)
    fig.suptitle("Time series: hybrid mode in action (1 km link, outages shown in red)", fontweight="bold")
    axs[1].plot(tt, lvl, color=INK, lw=1)
    axs[1].fill_between(tt, 0, lvl, color=SHADE)
    axs[1].set_ylabel("Pool (seconds of demand)")
    axs[1].set_xlabel("Time (minutes)")
    c.save(fig, "fig13_hybrid_timeseries.png", "Hybrid: messages go keyless by QSDC while the link is up; the pool only covers outages")


def fig14_finite_key(c):
    rows = pool_vs_jit_blocks()
    df = pd.DataFrame(rows, columns=["L", "pairs_s", "Q", "n_jit", "jit", "pool", "asym"])
    df.to_csv(os.path.join(c.out, "data", "finite_key_pool_vs_jit.csv"), index=False)
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.semilogy(df.L, df.asym.clip(lower=0.5), color=G2, ls=":", marker="o", ms=4, label="Asymptotic (infinite block) limit")
    ax.semilogy(df.L, df.pool.clip(lower=0.5), color=ACC, marker="D", ms=4, label="Pool: 1-hour blocks")
    ax.semilogy(df.L, df.jit.clip(lower=0.5), color=INK, ls="--", marker="s", ms=4, label="Just-in-time: 1-second blocks")
    ax.text(118, 6, "just-in-time:\n0 key from 150 km on", fontsize=8.5, color=INK, bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1.5))
    ax.set_ylim(0.4, 1e7)
    ax.set_xlabel("Fiber distance (km)")
    ax.set_ylabel("Secure key rate (bits/s, log)")
    ax.set_title("Pools also buy finite-key efficiency")
    ax.legend(loc="lower left")
    c.results["finite_key"] = df[["L", "jit", "pool", "asym"]].round(1).to_dict(orient="records")
    c.save(fig, "fig14_finite_key.png", "Pools allow large blocks: 1.8x more key at 100 km and key at 150-200 km where 1 s blocks give zero")


def fig15_memory_needed(c):
    from transports import compose
    xc = X["fig15"]
    p = werner_weights(xc["fidelity"])
    T2s = np.logspace(*xc["t2_grid_log10_s"])
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for wait, col, ls in zip(xc["outage_waits_s"], [INK, G1], ["-", "--"]):
        sec = [max(0, 2 - 2 * shannon(compose(p, 1 - np.exp(-wait / T2)))) for T2 in T2s]
        ax.semilogx(T2s, sec, color=col, ls=ls, label=f"Outage of {wait} s")
    ax.axhline(1 - shannon(p), color=ACC, lw=1)
    ax.text(12, 1 - shannon(p) + 0.05, "key mode, stored as classical bits: never decays", color=ACC, fontsize=8.5, bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1.5))
    ax.set_xlabel("Quantum memory coherence time T2 (s, log)")
    ax.set_ylabel("Secure bits per stored pair")
    ax.set_title("Why QSDC can't ride out outages: entanglement decays")
    ax.legend(loc="center right")
    c.save(fig, "fig15_memory_needed.png", "Buffering entanglement through 30-120 s outages needs T2 of ~1000 s or more; classical pools have no such limit")


def fig16_scheduling(c):
    xc = X["fig16"]
    T = xc["duration_s"][c.mode]
    rows = []
    for buf in xc["buffers_s"]:
        for margin in xc["margins"]:
            for s in ["equal_up", "lowest_pool_first"]:
                v = np.mean([schedule_sim(xc["receivers"], margin, buf, s, T=T, seed=sd)[0] for sd in range(X["n_seeds"])])
                rows.append(dict(buffer_s=buf, margin=margin, sched=s, on_time=v))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(c.out, "data", "multicast_scheduling.csv"), index=False)
    fig, ax = plt.subplots(figsize=(7.2, 4))
    for (m, s), g in df.groupby(["margin", "sched"]):
        col = ACC if s == "lowest_pool_first" else INK
        ls = "-" if m == max(xc["margins"]) else "--"
        ax.plot(g.buffer_s, g.on_time * 100, color=col, ls=ls, marker="o", ms=4, label=f"{'lowest-pool-first' if s != 'equal_up' else 'equal split'}, source {int((m-1)*100)}% over demand")
    ax.set_xlabel("Pool depth per receiver (seconds of demand)")
    ax.set_ylabel(f"All {xc['receivers']} receivers on time (%)")
    ax.set_title("Multicast: buffer depth matters, extra source capacity barely does")
    ax.legend(fontsize=8, loc="lower right")
    c.save(fig, "fig16_scheduling.png", "Growing buffer 10->120 s lifts on-time 40%->97%; adding 45% more source capacity changes it by ~2 points")


def fig17_pareto(c):
    import sweep as sw
    df = sw.df.copy()
    df.to_csv(os.path.join(c.out, "data", "design_space_sweep.csv"), index=False)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    d = df.fillna(0)
    sc = ax.scatter(d.rate_50km.clip(lower=0.3), d.security, c=d.on_time_4hop, cmap="Greys", vmin=0, vmax=1, s=14, edgecolor=G2, linewidth=0.3)
    best = d[(d.dist == "mdi") & (d.cert == "tomographic") & (d.monitor == "ml_telemetry") & (d.transport == "key_otp") & (d.auth == "wegman_carter_recycled") & (d.delivery == "multipath_pool_2of3")]
    ax.scatter(best.rate_50km, best.security, s=110, facecolor="none", edgecolor=ACC, linewidth=2, label="Recommended practical design")
    di = d[(d.dist == "di_heralded") & (d.transport == "key_otp") & (d.auth == "wegman_carter_recycled") & (d.monitor == "ml_telemetry") & (d.delivery == "e2e_swap_pool")]
    ax.scatter(di.rate_50km.clip(lower=0.3), di.security, s=90, marker="s", facecolor="none", edgecolor=INK, linewidth=1.5, label="Max-security (device-independent)")
    ax.set_xscale("log")
    ax.set_xlabel("Secure rate at 50 km (bits/s, log)")
    ax.set_ylabel("Security score (1 = no open attack class)")
    ax.set_title(f"All {len(df)} valid combinations")
    ax.text(1.3, 0.44, "far left = near-zero rate\n(ping-pong, device-independent)", fontsize=7.5, color=G1)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("On-time at 4 hops")
    ax.legend(loc="lower left", fontsize=8)
    c.results["sweep_size"] = int(len(df))
    c.save(fig, "fig17_design_space.png", "Every combination of distribution x certification x monitoring x transport x authentication x delivery, scored")


ALL = [fig01_rate_vs_distance, fig02_superdense_security, fig03_switch_rule, fig04_crossover_sensitivity, fig05_06_detection,
       fig07_on_time_vs_hops, fig08_pool_timeseries, fig09_pool_sizing, fig10_11_multicast, fig12_hybrid, fig14_finite_key,
       fig15_memory_needed, fig16_scheduling, fig17_pareto]


def main(out_dir="results", fast=False, only=None):
    c = Ctx(out_dir, fast)
    t0 = time.time()
    for f in ALL:
        if only and not any(o in f.__name__ for o in only):
            continue
        print(f"[{time.time() - t0:6.1f}s] {f.__name__}", flush=True)
        f(c)
    path = os.path.join(out_dir, "key_numbers.json")
    merged = {}
    if only and os.path.exists(path):
        with open(path) as fh:
            merged = json.load(fh)
        figs = {f["file"]: f for f in merged.get("figures", [])}
        for f in c.results.pop("figures", []):
            figs[f["file"]] = f
        merged["figures"] = sorted(figs.values(), key=lambda f: f["file"])
    merged.update(c.results)
    with open(path, "w") as fh:
        json.dump(merged, fh, indent=2, default=float)
    print(f"done in {time.time() - t0:.0f}s -> {out_dir}/")
    return c.results
