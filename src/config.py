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


def _values(node, name=""):
    if "value" in node:
        if not str(node.get("source", "")).strip():
            raise ValueError(f"{name}: missing source")
        _check(node["value"], name)
        return node["value"]
    return {k: _values(v, f"{name}.{k}" if name else k) for k, v in node.items()}


def load(path=PATH):
    with open(path, encoding="utf-8") as fh:
        return _values(yaml.safe_load(fh))


CFG = load()


def availability():
    o = CFG["outage"]
    return o["mean_up_s"] / (o["mean_up_s"] + o["mean_down_s"])
