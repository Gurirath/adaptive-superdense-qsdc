# Secure quantum communication: key sharing + superdense coding simulations

One command runs every simulation and saves 17 figures plus all numbers.

## Run it

```bash
pip install -r requirements.txt
python run_all.py
```

Takes about 1–3 minutes on a laptop. Everything lands in `results/`:

- `results/fig01…fig17_*.png` — the figures (200 dpi, ready for screenshots or slides)
- `results/key_numbers.json` — every headline number, plus a caption for each figure
- `results/data/*.csv` — the raw data behind each figure

Options:

```bash
python run_all.py --fast          # shorter simulations, about half the time
python run_all.py --only fig05    # regenerate just one figure (names: fig01 … fig17)
python run_all.py --out my_folder # save somewhere else
```

A pre-generated copy of all results is already included in `results/`, in case you want the figures without running anything.

## What each figure shows

| Figure | Type | What it shows |
| --- | --- | --- |
| fig01_rate_vs_distance | analytical | Secure bits/s vs fiber distance for key mode, superdense QSDC, DL04 and the adaptive switch; superdense wins below ~6 km |
| fig02_superdense_security | analytical | Density-matrix result: superdense gives 2× secure bits per pair; Eve capped at H(p) |
| fig03_switch_rule | analytical | Switching rule η* = 0.5, same for every fidelity |
| fig04_crossover_sensitivity | analytical | Max distance where superdense wins, by memory quality and Bell-measurement type |
| fig05_attack_timeseries | time series | 90 minutes of link telemetry with attacks; static threshold vs ML alarms |
| fig06_detection_comparison | analytical | Attack detection recall: static threshold 27%, 4-monitor thresholds 73%, ML 99% |
| fig07_on_time_vs_hops | analytical | On-time key delivery vs hops for 6 strategies; just-in-time falls as 0.909^hops |
| fig08_pool_timeseries | time series | One hour on a 4-hop path: outages, pool level, misses (just-in-time 40% vs pool 0.3%) |
| fig09_pool_sizing | analytical | Pool size needed; ~4× mean outage is enough |
| fig10_multicast_on_time | analytical | 1-to-N: group key on time vs number of receivers |
| fig11_ghz_vs_bipartite | heatmap | When GHZ conference keys beat separate links |
| fig12_hybrid_bars | analytical | QSDC + pool hybrid vs pool-only vs QSDC-only |
| fig13_hybrid_timeseries | time series | 40 minutes of the hybrid switching between keyless QSDC and pool keys |
| fig14_finite_key | analytical | Pools allow large blocks: more key, longer range |
| fig15_memory_needed | analytical | Quantum memory needed for QSDC to survive outages (~1000 s) |
| fig16_scheduling | analytical | Multicast: buffer depth matters, source capacity barely does |
| fig17_design_space | scatter | All 804 combinations: security vs rate vs on-time |

## Code layout

- `run_all.py` — entry point
- `src/figures.py` — builds every figure and the numbers file
- `src/core.py` — density matrices, Bell states, Holevo information, key-rate formulas
- `src/transports.py` — fiber link model and secure rate of each transport
- `src/detect.py` — synthetic telemetry, threshold detectors, ML detector
- `src/deliver.py`, `src/pools.py` — multi-hop outages and key pools
- `src/multicast.py` — 1-to-N group keys, GHZ vs bipartite
- `src/extend_net.py` — QSDC + pool hybrid, multicast scheduling
- `src/extend_theory.py` — finite-key effect, qudit switching threshold
- `src/sweep.py` — the full design-space sweep

Each `src/*.py` file can also be run on its own (for example `cd src && python transports.py`) to print its raw numbers.

## Assumptions

0.2 dB/km fiber, 0.85 detector efficiency, 1e-8 dark counts, 1% misalignment, 1 GHz clock, 0.01 pairs per pulse, 10 ms quantum memory with 0.9 efficiency, and link outages averaging 300 s up / 30 s down. Attack signatures in the telemetry are modelled, not measured on hardware. Results use fixed random seeds, so every run gives the same numbers.

See `SUMMARY.md` for the one-page summary of findings.
