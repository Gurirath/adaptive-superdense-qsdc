import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score
from config import CFG

DT = CFG["detection"]

ATTACKS = {0: "benign", 1: "intercept_resend", 2: "detector_blinding", 3: "trojan_horse"}


def telemetry(T=DT["duration_s"], seed=DT["seed"], attack_rate=1 / DT["mean_attack_interval_s"]):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    drift_pol = DT["drift_amplitude"] * (1 + np.sin(2 * np.pi * t / DT["drift_period_s"] + rng.uniform(*DT["drift_phase"]))) + np.cumsum(rng.normal(0, DT["drift_walk_sigma"], T)).clip(-DT["drift_walk_clip"], DT["drift_walk_clip"])
    raman = np.zeros(T)
    i = 0
    while i < T:
        i += int(rng.exponential(DT["raman_mean_interval_s"]))
        if i >= T:
            break
        d = int(rng.uniform(*DT["raman_duration_s"]))
        raman[i:i + d] += rng.uniform(*DT["raman_amplitude"])
        i += d
    label = np.zeros(T, dtype=int)
    strength = np.zeros(T)
    i = 0
    while i < T:
        i += int(rng.exponential(1 / attack_rate))
        if i >= T:
            break
        d = int(rng.uniform(*DT["attack_duration_s"]))
        label[i:i + d] = rng.integers(*DT["attack_type_codes"])
        strength[i:i + d] = rng.uniform(*DT["attack_strength"])
        i += d
    sifted = DT["sifted_per_s"]
    singles0 = DT["singles_per_s"]
    dark0 = DT["dark_per_s"]
    noise_counts = dark0 * (1 + raman)
    acc_frac = noise_counts / (noise_counts + DT["accidental_reference_counts"])
    ez = DT["base_error"] + DT["accidental_error"] * acc_frac
    ex = DT["base_error"] + drift_pol + DT["accidental_error"] * acc_frac
    singles = singles0 + noise_counts * DT["singles_per_noise_count"]
    dark = noise_counts.copy()
    dbl = DT["double_click_fraction"] * sifted * (1 + raman * DT["double_click_raman_factor"])
    backrefl = DT["backreflection_mean"] + rng.normal(0, DT["backreflection_sigma"], T)
    ir = label == 1
    ez[ir] += strength[ir] / DT["intercept_resend_error_divisor"]
    ex[ir] += strength[ir] / DT["intercept_resend_error_divisor"]
    bl = label == 2
    dark[bl] *= DT["blinding_dark_factor"]
    dbl[bl] *= DT["blinding_double_click_factor"]
    ez[bl] *= DT["blinding_error_factor"]
    ex[bl] *= DT["blinding_error_factor"]
    singles[bl] *= 1 - DT["blinding_singles_factor"] * strength[bl]
    th = label == 3
    backrefl[th] += DT["trojan_backreflection_factor"] * strength[th]
    ex[th] += strength[th] / DT["trojan_error_divisor"]
    obs = pd.DataFrame({
        "qz": rng.binomial(sifted, np.clip(ez, *DT["error_clip"])) / sifted,
        "qx": rng.binomial(sifted, np.clip(ex, *DT["error_clip"])) / sifted,
        "singles": rng.poisson(singles),
        "dark": rng.poisson(dark),
        "dbl": rng.poisson(dbl),
        "backrefl": backrefl,
    })
    V = 1 - obs.qz - obs.qx
    obs["S"] = 2 * np.sqrt(2) * V.clip(0, 1) + rng.normal(0, DT["chsh_noise_sigma"], T)
    obs["label"] = label
    return obs


def features(o, w=tuple(DT["feature_windows_s"])):
    f = pd.DataFrame(index=o.index)
    base = ["qz", "qx", "singles", "dark", "dbl", "backrefl", "S"]
    for c in base:
        f[c] = o[c]
        for k in w:
            m = o[c].rolling(k, min_periods=1).mean()
            f[f"{c}_m{k}"] = m
            f[f"{c}_d{k}"] = o[c] - o[c].rolling(DT["baseline_window_s"], min_periods=1).median()
    f["q_sum"] = o.qz + o.qx
    f["q_diff"] = o.qx - o.qz
    f["q_per_dark"] = (o.qz + o.qx) / (o.dark + 1)
    f["dark_per_singles"] = o.dark / o.singles
    f["dbl_per_dark"] = o.dbl / (o.dark + 1)
    for k in DT["correlation_windows_s"]:
        f[f"corr_qz_dark_{k}"] = o.qz.rolling(k, min_periods=DT["correlation_min_periods"]).corr(o.dark).fillna(0)
    return f


def static_threshold(o, fa=DT["false_alarm"], train=None):
    q = o.qz + o.qx
    thr = np.quantile((train.qz + train.qx)[train.label == 0], 1 - fa)
    return (q > thr).astype(int)


def multi_threshold(o, fa=DT["false_alarm"], train=None):
    b = train[train.label == 0]
    per = fa / DT["multi_monitor_count"]
    flags = ((o.qz + o.qx) > np.quantile(b.qz + b.qx, 1 - per)) | (o.dark < np.quantile(b.dark, per)) | (o.dbl < np.quantile(b.dbl, per)) | (o.backrefl > np.quantile(b.backrefl, 1 - per))
    return flags.astype(int)


def cusum(o, fa=DT["false_alarm"], train=None):
    b = train[train.label == 0]
    def resid(d):
        x = d.qz + d.qx
        return (x - x.rolling(DT["baseline_window_s"], min_periods=1).median()).reset_index(drop=True)
    rb = resid(train)[train.label.values == 0]
    q = resid(o)
    mu = 0.0
    sd = rb.std()

    def run(series, h):
        s, out = 0.0, np.zeros(len(series), dtype=int)
        for i, v in enumerate(series):
            s = max(0.0, s + (v - mu) / sd - DT["cusum_slack"])
            out[i] = s > h
            if s > DT["cusum_cap_factor"] * h:
                s = DT["cusum_cap_factor"] * h
        return out

    tq = rb.values
    lo, hi = DT["cusum_search"]
    for _ in range(DT["cusum_search_steps"]):
        h = (lo + hi) / 2
        if run(tq, h).mean() > fa:
            lo = h
        else:
            hi = h
    return run(q.values, hi)


def evaluate(pred, y):
    out = {"false_alarm": float(pred[y == 0].mean())}
    for k in (1, 2, 3):
        m = y == k
        out[ATTACKS[k] + "_recall"] = float(pred[m].mean()) if m.any() else np.nan
    out["overall_recall"] = float(pred[y > 0].mean())
    out["precision"] = float(precision_score(y > 0, pred, zero_division=0))
    return out


def run(seeds_train=tuple(DT["train_seeds"]), seeds_test=tuple(DT["test_seeds"]), fa=DT["false_alarm"], seed_val=DT["validation_seed"]):
    tr_list = [telemetry(seed=s) for s in seeds_train]
    tr = pd.concat(tr_list, ignore_index=True)
    te_list = [telemetry(seed=s) for s in seeds_test]
    te = pd.concat(te_list, ignore_index=True)
    va = telemetry(seed=seed_val)
    Ftr = pd.concat([features(o) for o in tr_list], ignore_index=True)
    Fte = pd.concat([features(o) for o in te_list], ignore_index=True)
    Fva = features(va)
    clf = HistGradientBoostingClassifier(max_iter=DT["classifier_max_iter"], learning_rate=DT["classifier_learning_rate"], class_weight="balanced", random_state=DT["classifier_random_state"])
    clf.fit(Ftr, tr.label)
    proba_va = 1 - clf.predict_proba(Fva)[:, 0]
    proba_te = 1 - clf.predict_proba(Fte)[:, 0]
    thr = np.quantile(proba_va[va.label.values == 0], 1 - fa)
    rows = {}
    rows["static_qber_threshold"] = evaluate(static_threshold(te, fa, tr).values, te.label.values)
    rows["cusum_qber"] = evaluate(cusum(te, fa, tr), te.label.values)
    rows["multi_monitor_thresholds"] = evaluate(multi_threshold(te, fa, tr).values, te.label.values)
    rows["ml_gradient_boosting"] = evaluate((proba_te > thr).astype(int), te.label.values)
    pred_cls = clf.predict(Fte)
    m = te.label.values > 0
    rows["ml_attack_type_accuracy"] = {"accuracy_on_attacked_windows": float((pred_cls[m] == te.label.values[m]).mean())}
    return pd.DataFrame(rows).T, clf, thr


if __name__ == "__main__":
    res, _, _ = run()
    pd.set_option("display.width", 200)
    print(res.round(3))
    res.to_csv("out_detection.csv")
