import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
os.chdir(HERE)

from figures import main

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run every simulation and save all figures to results/")
    ap.add_argument("--fast", action="store_true", help="shorter simulations (about half the runtime)")
    ap.add_argument("--only", nargs="*", help="run only figures whose function name contains these strings, e.g. fig07 fig12")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    main(a.out, a.fast, a.only)
