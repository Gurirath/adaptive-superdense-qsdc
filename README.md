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

## Parameters and their sources

Every model parameter lives in `config.yaml`. The simulation code holds no parameter values of its own; it reads them through `src/config.py`.

Each entry has a `value` and a `source`, and may have a `unit` and a `note`:

```yaml
link:
  alpha_db_km:
    value: 0.2
    unit: dB/km
    source: "Gisin, N., Ribordy, G., Tittel, W., Zbinden, H. (2002). Quantum cryptography. ..."
    note: "The review gives 0.2 dB/km as the attenuation of standard telecom fibre at 1550 nm."
```

A `source` is one of two things:

- A published reference with authors, year, title and DOI. Each one was checked against its DOI record and against the paper's abstract or full text. Where the paper supports a value without stating it exactly, the `note` says so.
- The word `assumption` followed by a one-line reason. This covers design choices, modelled quantities and anything for which no reference could be verified.

Five values carry a published reference: fibre attenuation, detector efficiency, Bell-measurement efficiency, the finite-key correction coefficient and the error-correction efficiency. Everything else is an assumption and is labelled as one.

The sections of `config.yaml` are:

| Section | What it holds |
| --- | --- |
| `link` | Fibre, source, detector and memory parameters of one link |
| `transport` | Settings of the rate model shared by all transports |
| `numerics` | Numerical guards and grid sizes |
| `outage` | Mean up time and mean outage length of a link |
| `delivery`, `pools` | Multi-hop delivery and key-pool settings |
| `multicast`, `hybrid`, `scheduling` | 1-to-N, QSDC + pool hybrid and shared-source scheduling settings |
| `finite_key` | Finite-key security and block-size settings |
| `detection` | Synthetic telemetry, attack signatures and detector settings |
| `sweep` | Scoring inputs and exposure weights of the design-space sweep |
| `experiments` | Grids, durations and seeds used by each figure |
| `standalone` | Values used only when a module is run on its own |

To try a different value, edit its `value` in `config.yaml` and re-run. Write numbers with an exponent as `1.0e-8`, not `1e-8`: the YAML reader treats the second form as text, and the loader stops with an error if it finds text where a number should be.

Mathematical constants stay in the code because they are part of the formulas, not choices: the factor of 10 in decibel conversion, the Werner-state and depolarising-channel coefficients, 0.5 as the largest possible error rate, and array dimensions. Plot styling in `src/figures.py` (figure sizes, colours, label positions) also stays in the code.

Moving the parameters into `config.yaml` did not change any result: the figures, the CSV files and `results/key_numbers.json` are byte-for-byte the same as before.

## Code layout

- `run_all.py` — entry point
- `config.yaml` — every parameter, with its source
- `src/config.py` — loads `config.yaml` and checks that every entry has a numeric value and a source
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

0.2 dB/km fiber, 0.85 detector efficiency, 1e-8 dark counts, 1% misalignment, 1 GHz clock, 0.01 pairs per pulse, 10 ms quantum memory with 0.9 efficiency, and link outages averaging 300 s up / 30 s down. Attack signatures in the telemetry are modelled, not measured on hardware. Results use fixed random seeds, so every run gives the same numbers. The full list, with the source of each value, is in `config.yaml`.

See `SUMMARY.md` for the one-page summary of findings.
