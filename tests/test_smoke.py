import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_run_all_fast_completes_and_writes_every_output(tmp_path):
    out = tmp_path / "results"
    done = subprocess.run([sys.executable, os.path.join(ROOT, "run_all.py"), "--fast", "--out", str(out)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-2000:]
    figures = sorted(p.name for p in out.glob("fig*.png"))
    assert len(figures) == 17
    numbers = json.loads((out / "key_numbers.json").read_text())
    assert len(numbers["figures"]) == 17
    assert numbers["sweep_size"] > 0
