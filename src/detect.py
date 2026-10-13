import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score

ATTACKS = {0: "benign", 1: "intercept_resend", 2: "detector_blinding", 3: "trojan_horse"}


def telemetry(T=86400, seed=0, attack_rate=1 / 1800):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    drift_pol = 0.004 * (1 + np.sin(2 * np.pi * t / 86400 + rng.uniform(0, 6))) + np.cumsum(rng.normal(0, 2e-5, T)).clip(-0.004, 0.004)
    raman = np.zeros(T)
    i = 0
    while i < T:
        i += int(rng.exponential(1200))
        if i >= T:
            break
        d = int(rng.uniform(10, 120))
        raman[i:i + d] += rng.uniform(0.5, 3.0)
        i += d
    label = np.zeros(T, dtype=int)
    strength = np.zeros(T)
    i = 0
    while i < T:
        i += int(rng.exponential(1 / attack_rate))
        if i >= T:
            break
        d = int(rng.uniform(5, 60))
        label[i:i + d] = rng.integers(1, 4)
        strength[i:i + d] = rng.uniform(0.02, 0.12)
        i += d
    sifted = 20000
    singles0 = 2e5
    dark0 = 200.0
    noise_counts = dark0 * (1 + raman)
    acc_frac = noise_counts / (noise_counts + 2e4)
    ez = 0.008 + 0.5 * acc_frac
    ex = 0.008 + drift_pol + 0.5 * acc_frac
    singles = singles0 + noise_counts * 50
    dark = noise_counts.copy()
    dbl = 5e-4 * sifted * (1 + raman * 0.5)
    backrefl = 1.0 + rng.normal(0, 0.05, T)
    ir = label == 1
    ez[ir] += strength[ir] / 4
    ex[ir] += strength[ir] / 4
    bl = label == 2
    dark[bl] *= 0.05
    dbl[bl] *= 0.05
    ez[bl] *= 0.7
    ex[bl] *= 0.7
    singles[bl] *= 1 - 0.5 * strength[bl]
    th = label == 3
    backrefl[th] += 3 * strength[th]
    ex[th] += strength[th] / 10
    obs = pd.DataFrame({
        "qz": rng.binomial(sifted, np.clip(ez, 0, 0.5)) / sifted,
        "qx": rng.binomial(sifted, np.clip(ex, 0, 0.5)) / sifted,
        "singles": rng.poisson(singles),
        "dark": rng.poisson(dark),
        "dbl": rng.poisson(dbl),
        "backrefl": backrefl,
    })
    V = 1 - obs.qz - obs.qx
    obs["S"] = 2 * np.sqrt(2) * V.clip(0, 1) + rng.normal(0, 0.01, T)
    obs["label"] = label
    return obs


def features(o, w=(5, 15, 60)):
    f = pd.DataFrame(index=o.index)
    base = ["qz", "qx", "singles", "dark", "dbl", "backrefl", "S"]
    for c in base:
        f[c] = o[c]
        for k in w:
            m = o[c].rolling(k, min_periods=1).mean()
            f[f"{c}_m{k}"] = m
            f[f"{c}_d{k}"] = o[c] - o[c].rolling(600, min_periods=1).median()
    f["q_sum"] = o.qz + o.qx
    f["q_diff"] = o.qx - o.qz
    f["q_per_dark"] = (o.qz + o.qx) / (o.dark + 1)
    f["dark_per_singles"] = o.dark / o.singles
    f["dbl_per_dark"] = o.dbl / (o.dark + 1)
    for k in (15, 60):
        f[f"corr_qz_dark_{k}"] = o.qz.rolling(k, min_periods=3).corr(o.dark).fillna(0)
    return f


def static_threshold(o, fa=0.01, train=None):
    q = o.qz + o.qx
    thr = np.quantile((train.qz + train.qx)[train.label == 0], 1 - fa)
    return (q > thr).astype(int)


def multi_threshold(o, fa=0.01, train=None):
    b = train[train.label == 0]
    per = fa / 4
    flags = ((o.qz + o.qx) > np.quantile(b.qz + b.qx, 1 - per)) | (o.dark < np.quantile(b.dark, per)) | (o.dbl < np.quantile(b.dbl, per)) | (o.backrefl > np.quantile(b.backrefl, 1 - per))
    return flags.astype(int)


def cusum(o, fa=0.01, train=None):
    b = train[train.label == 0]
    def resid(d):
        x = d.qz + d.qx
        return (x - x.rolling(600, min_periods=1).median()).reset_index(drop=True)
    rb = resid(train)[train.label.values == 0]
    q = resid(o)
    mu = 0.0
    sd = rb.std()

    def run(series, h):
        s, out = 0.0, np.zeros(len(series), dtype=int)
        for i, v in enumerate(series):
            s = max(0.0, s + (v - mu) / sd - 0.5)
            out[i] = s > h
            if s > 3 * h:
                s = 3 * h
        return out

    tq = rb.values
    lo, hi = 0.5, 200.0
    for _ in range(30):
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


def run(seeds_train=(1, 2, 3), seeds_test=(11, 12), fa=0.01, seed_val=21):
    tr_list = [telemetry(seed=s) for s in seeds_train]
    tr = pd.concat(tr_list, ignore_index=True)
    te_list = [telemetry(seed=s) for s in seeds_test]
    te = pd.concat(te_list, ignore_index=True)
    va = telemetry(seed=seed_val)
    Ftr = pd.concat([features(o) for o in tr_list], ignore_index=True)
    Fte = pd.concat([features(o) for o in te_list], ignore_index=True)
    Fva = features(va)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, class_weight="balanced", random_state=0)
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
