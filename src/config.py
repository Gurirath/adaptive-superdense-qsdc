import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")


def _check(value, name):
    if isinstance(value, str):
        raise ValueError(f"{name}: value {value!r} is text, not a number (write exponents as 1.0e-8)")
    if isinstance(value, dict):
        for k, v in value.items():
            _check(v, f"{name}.{k}")
    if isinstance(value, list):
        for v in value:
            _check(v, name)


def _values(node, field, name):
    if "value" in node:
        if not str(node.get(field, "")).strip():
            raise ValueError(f"{name}: missing {field}")
        _check(node["value"], name)
        return node["value"]
    return {k: _values(v, field, f"{name}.{k}") for k, v in node.items()}


def _merge(a, b, name=""):
    out = dict(a)
    for k, v in b.items():
        if k not in out:
            out[k] = v
        elif isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v, f"{name}{k}.")
        else:
            raise ValueError(f"{name}{k}: defined in more than one section")
    return out


def load(path=PATH):
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    _check(raw["simulation"], "simulation")
    for name, formula in raw.get("formulas", {}).items():
        if not str(formula.get("source", "")).strip():
            raise ValueError(f"formulas.{name}: missing source")
    merged = _merge(_values(raw["physics"], "source", "physics"), _values(raw["design"], "reason", "design"))
    return _merge(merged, raw["simulation"])


CFG = load()


def availability():
    o = CFG["outage"]
    return o["mean_up_s"] / (o["mean_up_s"] + o["mean_down_s"])
