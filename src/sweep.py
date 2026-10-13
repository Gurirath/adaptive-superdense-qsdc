import itertools
import numpy as np
import pandas as pd
from transports import Link, rates_at
from deliver import mean_on_time
from config import CFG

SW = CFG["sweep"]
EXP = SW["exposure"]

lk = Link()
DISTS = ["direct", "mdi", "di_heralded"]
CERTS = {"direct": ["bbm92", "tomographic"], "mdi": ["bbm92", "tomographic"], "di_heralded": ["di"]}
MONITORS = ["static_qber", "multi_monitor", "ml_telemetry"]
TRANSPORTS = ["key_otp", "two_step_sdc", "adaptive", "dl04", "ping_pong"]
AUTHS = ["none", "pqc_signature", "wegman_carter_recycled", "qia_entanglement"]
DELIVERY = ["jit_trusted_relay", "pool_trusted_relay", "multipath_pool_2of3", "e2e_swap_pool", "pool_pqc_fallback"]

SIMULATED = {
    "jit_trusted_relay": "jit_trusted_relay",
    "pool_trusted_relay": "pool_trusted_relay",
    "multipath_pool_2of3": "multipath_pool_k_of_n",
    "e2e_swap_pool": "pool_end_to_end_swap",
}


def on_time_table(mode="full"):
    T = CFG["experiments"]["fig07"]["duration_s"][mode]
    table = {d: mean_on_time(SW["on_time_hops"], s, T) for d, s in SIMULATED.items()}
    table["pool_pqc_fallback"] = SW["pqc_fallback_on_time"]
    return table


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
        return SW["ping_pong_rate"]


def attacks(dist, monitor, transport, auth, delivery):
    two_way = transport in ("two_step_sdc", "adaptive", "dl04", "ping_pong")
    det = EXP["detector_side_channel"]["direct_by_monitor"][monitor] if dist == "direct" else EXP["detector_side_channel"]["other"]
    trojan_base = EXP["trojan_horse"]["two_way"] if two_way else EXP["trojan_horse"]["one_way"]
    trojan = trojan_base * EXP["trojan_horse"]["monitor_factor"][monitor]
    a = {
        "channel_eavesdrop": EXP["channel_eavesdrop"]["ping_pong"] if transport == "ping_pong" else EXP["channel_eavesdrop"]["other"],
        "detector_side_channel": det,
        "trojan_horse": trojan,
        "source_side_channel": EXP["source_side_channel"]["dl04"] if transport == "dl04" else (EXP["source_side_channel"]["mdi"] if dist == "mdi" else EXP["source_side_channel"]["other"]),
        "mitm": EXP["mitm"][auth],
        "relay_compromise": EXP["relay_compromise"][delivery],
        "key_at_rest": EXP["key_at_rest"]["keyless_transport"] if transport in ("two_step_sdc", "dl04", "ping_pong") else (EXP["key_at_rest"]["pool_delivery"] if "pool" in delivery else EXP["key_at_rest"]["other"]),
        "fallback_computational": EXP["fallback_computational"]["pool_pqc_fallback"] if delivery == "pool_pqc_fallback" else EXP["fallback_computational"]["other"],
    }
    return a


def on_time(transport, delivery, table):
    if transport in ("two_step_sdc", "dl04", "ping_pong"):
        return table["jit_trusted_relay"] if delivery == "jit_trusted_relay" else SW["qsdc_non_jit_on_time"]
    return table[delivery]


def build(mode="full"):
    table = on_time_table(mode)
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
                cache[key] = tuple(rate(dist, cert, transport, L) for L in SW["rate_distances_km"])
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
                        "on_time_4hop": on_time(transport, delivery, table),
                    })

    return pd.DataFrame(rows)


def pareto(d, cols):
    vals = d[cols].values
    keep = np.ones(len(d), dtype=bool)
    for i in range(len(d)):
        dominated = ((vals >= vals[i]).all(axis=1) & (vals > vals[i]).any(axis=1)).any()
        keep[i] = not dominated
    return d[keep]


if __name__ == "__main__":
    df = build()
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
