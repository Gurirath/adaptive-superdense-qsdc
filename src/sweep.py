import itertools
import numpy as np
import pandas as pd
from transports import Link, rates_at

lk = Link()
DISTS = ["direct", "mdi", "di_heralded"]
CERTS = {"direct": ["bbm92", "tomographic"], "mdi": ["bbm92", "tomographic"], "di_heralded": ["di"]}
MONITORS = ["static_qber", "multi_monitor", "ml_telemetry"]
TRANSPORTS = ["key_otp", "two_step_sdc", "adaptive", "dl04", "ping_pong"]
AUTHS = ["none", "pqc_signature", "wegman_carter_recycled", "qia_entanglement"]
DELIVERY = ["jit_trusted_relay", "pool_trusted_relay", "multipath_pool_2of3", "e2e_swap_pool", "pool_pqc_fallback"]

ON_TIME_4HOP = {
    "jit_trusted_relay": 0.674,
    "pool_trusted_relay": 0.987,
    "multipath_pool_2of3": 1.0,
    "e2e_swap_pool": 0.241,
    "pool_pqc_fallback": 1.0,
}
ITS_FRACTION = {"pool_pqc_fallback": 0.987}
QSDC_JIT_4HOP = 0.906 ** 4


def rate(dist, cert, transport, L):
    r = rates_at(L, lk, cert, dist)
    if transport == "key_otp":
        return r["key_mode"]
    if transport == "two_step_sdc":
        return r["sdc_two_step"]
    if transport == "adaptive":
        return r["adaptive"]
    if transport == "dl04":
        return r["dl04"]
    if transport == "ping_pong":
        return 0.0


def attacks(dist, monitor, transport, auth, delivery):
    two_way = transport in ("two_step_sdc", "adaptive", "dl04", "ping_pong")
    det = {"static_qber": 1.0, "multi_monitor": 0.5, "ml_telemetry": 0.5}[monitor] if dist == "direct" else 0.0
    trojan_base = 1.0 if two_way else 0.5
    trojan = trojan_base * {"static_qber": 1.0, "multi_monitor": 0.5, "ml_telemetry": 0.5}[monitor]
    a = {
        "channel_eavesdrop": 1.0 if transport == "ping_pong" else 0.0,
        "detector_side_channel": det,
        "trojan_horse": trojan,
        "source_side_channel": 0.5 if transport == "dl04" else (0.25 if dist == "mdi" else 0.0),
        "mitm": {"none": 1.0, "pqc_signature": 0.25, "wegman_carter_recycled": 0.0, "qia_entanglement": 0.0}[auth],
        "relay_compromise": {"jit_trusted_relay": 1.0, "pool_trusted_relay": 1.0, "multipath_pool_2of3": 0.33, "e2e_swap_pool": 0.0, "pool_pqc_fallback": 1.0}[delivery],
        "key_at_rest": 0.0 if transport in ("two_step_sdc", "dl04", "ping_pong") else (0.25 if "pool" in delivery else 0.0),
        "fallback_computational": 0.25 if delivery == "pool_pqc_fallback" else 0.0,
    }
    return a


def on_time(transport, delivery):
    if transport in ("two_step_sdc", "dl04", "ping_pong"):
        return QSDC_JIT_4HOP if delivery == "jit_trusted_relay" else 0.0
    return ON_TIME_4HOP[delivery]


rows = []
cache = {}
for dist in DISTS:
    for cert in CERTS[dist]:
        for transport in TRANSPORTS:
            if dist == "di_heralded" and transport in ("two_step_sdc", "adaptive", "dl04"):
                continue
            if dist == "mdi" and transport == "dl04":
                continue
            key = (dist, cert, transport)
            cache[key] = (rate(dist, cert, transport, 10.0), rate(dist, cert, transport, 50.0))
            for monitor, auth, delivery in itertools.product(MONITORS, AUTHS, DELIVERY):
                if transport in ("two_step_sdc", "dl04", "ping_pong") and delivery not in ("jit_trusted_relay", "e2e_swap_pool"):
                    continue
                a = attacks(dist, monitor, transport, auth, delivery)
                r10, r50 = cache[key]
                rows.append({
                    "dist": dist, "cert": cert, "monitor": monitor, "transport": transport, "auth": auth, "delivery": delivery,
                    "security": 1 - np.mean(list(a.values())),
                    "worst_open": max(a, key=a.get) if max(a.values()) > 0 else "none",
                    "worst_level": max(a.values()),
                    "rate_10km": r10, "rate_50km": r50,
                    "on_time_4hop": on_time(transport, delivery),
                })

df = pd.DataFrame(rows)


def pareto(d, cols):
    vals = d[cols].values
    keep = np.ones(len(d), dtype=bool)
    for i in range(len(d)):
        dominated = ((vals >= vals[i]).all(axis=1) & (vals > vals[i]).any(axis=1)).any()
        keep[i] = not dominated
    return d[keep]


if __name__ == "__main__":
    print("total combinations:", len(df))
    df.to_csv("out_sweep.csv", index=False)
    cols = ["security", "rate_10km", "rate_50km", "on_time_4hop"]
    pf = pareto(df.fillna(0), cols).sort_values(["security", "on_time_4hop", "rate_50km"], ascending=False)
    pd.set_option("display.width", 250)
    print("pareto size:", len(pf))
    print(pf.head(25).round(3).to_string())
    print()
    top = df.sort_values(["security", "on_time_4hop", "rate_50km"], ascending=False).head(15)
    print(top.round(3).to_string())
    print()
    best_by_transport = df.sort_values(["security", "on_time_4hop", "rate_50km"], ascending=False).groupby("transport").head(1)
    print(best_by_transport.round(3).to_string())
    print()
    print(df.groupby("transport")[["security", "on_time_4hop", "rate_10km", "rate_50km"]].max().round(3).to_string())
