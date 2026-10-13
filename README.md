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

The file has three top-level sections:

- `physics` holds claims about the world: real hardware, channels, attacks and security bounds. Every entry states where its value comes from.
- `design` holds choices about how the system is built or analysed: buffer and pool depths, demand and load levels, pool capacities, the multipath 2-of-3 choice, the detector's feature windows and classifier settings, the false-alarm budget. Every entry gives a short reason. These are not claims that need evidence; a different designer could pick differently.
- `simulation` holds how the model is run and plotted: seeds, durations, grids, numerical tolerances and the cases each figure shows. These are plain values with no source or reason.

A fourth section, `formulas`, holds no numbers. It records where the approximations in the swapping model come from, each with an `expression` and a `source`.

A `physics` entry has a `value` and a `source`, and may have a `unit` and a `note`. A `design` entry has a `value` and a `reason`, and may have a `unit`. A `simulation` entry is just a value:

```yaml
physics:
  link:
    alpha_db_km:
      value: 0.2
      unit: "dB/km"
      source: "Gisin, N., Ribordy, G., Tittel, W., Zbinden, H. (2002). Quantum cryptography. ..."
      note: "The review gives 0.2 dB/km as the attenuation of standard telecom fibre at 1550 nm."

design:
  delivery:
    k_of_n:
      value: 2
      reason: "number of paths that must deliver in the multipath strategies"

simulation:
  delivery:
    duration_s: 100000
    seed: 0
```

A `source` is one of two things:

- A published reference with authors, year, title and a DOI or arXiv number. Each one was checked against its DOI or arXiv record and against the paper's abstract or full text. Where the paper supports a value without stating it exactly, the `note` says so.
- The word `assumption` followed by a one-line reason. This covers design choices, modelled quantities and anything for which no reference could be verified.

The file has 62 physics parameters, 37 design choices and 90 simulation settings. Eight physics parameters carry a published reference:

| Parameter | Value | Reference |
| --- | --- | --- |
| Fibre attenuation | 0.2 dB/km | Gisin et al. 2002, Rev. Mod. Phys. 74, 145 |
| Detector efficiency | 0.85 | Marsili et al. 2013, Nature Photonics 7, 210 |
| Dark-count probability | 1e-8 per pulse | Grasselli and Curty 2019, New J. Phys. 21, 073001 |
| Memory efficiency | 0.9 | Wang et al. 2019, Nature Photonics 13, 346 |
| Bell-measurement efficiency | 0.5 | Calsamiglia and Lütkenhaus 2001, Appl. Phys. B 72, 67 |
| Ping-pong round-trip bound | 0.75 | Zhang 2004, arXiv:quant-ph/0402099 |
| Finite-key correction coefficient | 7 | Scarani and Renner 2008, Phys. Rev. Lett. 100, 200501 |
| Error-correction efficiency | 1.16 | Lim et al. 2014, Phys. Rev. A 89, 022307 |

The other 54 physics parameters are assumptions and are labelled as such. Most of them are the modelled telemetry and attack signatures and the judgement scores of the design-space sweep.

Three of the references support a value without measuring it. For the detector and memory efficiencies the papers show the value is achievable but do not state that exact number. For the dark-count probability the paper uses 1e-8 as an illustrative value with no experimental basis. The notes in `config.yaml` say so in each case.

All three sections use the same group names, and the code sees them merged, so `delivery` contains its physics parameters, its design choices and its simulation settings together:

| Group | What it holds |
| --- | --- |
| `link` | Fibre, source, detector and memory parameters of one link |
| `transport` | Settings of the rate model shared by all transports |
| `numerics` | Numerical guards and grid sizes |
| `outage` | Mean up time and mean outage length of a link |
| `delivery`, `pools` | Multi-hop delivery and key-pool settings |
| `multicast`, `hybrid`, `scheduling` | 1-to-N, QSDC + pool hybrid and shared-source scheduling settings |
| `finite_key` | Finite-key security and block-size settings |
| `detection` | Synthetic telemetry, attack signatures and detector settings |
| `sweep` | Exposure weights and scoring settings of the design-space sweep |
| `experiments` | Grids, durations, seeds and displayed cases of each figure |
| `standalone` | Values used only when a module is run on its own |

The design-space sweep (fig17) does not store on-time delivery figures. It computes them when it runs, by calling the same delivery simulation as fig07 at 4 hops with the same duration and seeds, so the two always agree. Keyless transports use the just-in-time trusted-relay result. The one exception is delivery with a post-quantum fallback, which is on time by construction and is set to 1 in `config.yaml`.

To try a different value, edit it in `config.yaml` and re-run. Write numbers with an exponent as `1.0e-8`, not `1e-8`: the YAML reader treats the second form as text, and the loader stops with an error if it finds text where a number should be.

Mathematical constants stay in the code because they are part of the formulas, not choices: the factor of 10 in decibel conversion, the Werner-state and depolarising-channel coefficients, 0.5 as the largest possible error rate, and array dimensions. Plot styling in `src/figures.py` (figure sizes, colours, label positions) also stays in the code.

Moving the parameters into `config.yaml` did not change any result. Two later changes to the model did, and only where expected:

- Computing the sweep's on-time figures at run time changed the on-time column of `results/data/design_space_sweep.csv` and the shading in fig17.
- The swapping model described below changed the on-time delivery of end-to-end swapping with a pool, which appears in fig07, `results/data/on_time_vs_hops.csv`, `results/key_numbers.json` and the sweep.

Every other figure, CSV file and number is byte-for-byte the same as before.

## Entanglement swapping with memories

`swap_memory_model` in `src/deliver.py` gives the key rate of a path of h links joined by entanglement swapping when every node has a quantum memory. It is used by two delivery strategies: just-in-time swapping with memory, and end-to-end swapping that fills a key pool.

Each link creates pairs independently, succeeding on each clock cycle with probability p = mu × link transmission × detector efficiency. With memories, a link that succeeds holds its pair until all h links have one, and only then are the swaps done. The expected number of attempts until all h links have succeeded is taken as H_h / p, where H_h = 1 + 1/2 + ... + 1/h is the h-th harmonic number. This approximation is valid when p is small. Sangouard et al. 2011 (Rev. Mod. Phys. 83, 33) give the two cases H_2 = 3/2 and H_4 = 25/12 explicitly; the general form for h links is the same result and is not written out in that review.

Three effects then reduce the rate:

- Memory decoherence. While waiting, a stored pair is depolarised with probability q_m = 1 − exp(−t_wait / T2), where t_wait is the waiting time and T2 the memory coherence time. This is applied to every link pair for the full wait, which overstates the loss for the pairs created last. At one hop nothing is stored, so there is no decoherence.
- Swapping. Each of the h − 1 swaps succeeds with the Bell-measurement efficiency. Every link pair is treated as a Werner state, and the end-to-end pair's Werner parameter is the product of the link pairs' parameters, so fidelity falls with every hop.
- Memory readout. Each intermediate node reads out two stored halves for its swap, so the rate is multiplied by the memory efficiency to the power 2(h − 1). There is no factor at one hop.

The end-to-end fidelity is turned into a secret fraction with the tomographic key-rate function in `src/core.py`, the same one used for the per-hop key rate. Swapping without memory keeps its flat key fraction of 0.8 per pair.

The finding is that the memory's coherence time is not what limits swapping here. With T2 = 10 ms and 25 km hops, the wait is about 1 microsecond, so decoherence is of order 1e-4 and has no visible effect. The rate at 25 km per hop is:

| Hops | With memory (bits/s) | Without memory (bits/s) | Meets 256 kbit/s demand |
| --- | --- | --- | --- |
| 1 | 2,321,901 | 2,150,349 | both |
| 2 | 551,157 | 289,000 | both |
| 3 | 160,720 | 38,841 | neither |
| 4 | 50,229 | 5,220 | neither |
| 10 | 54 | 0.03 | neither |

Memories raise the rate at every path length, by about 10 times at 4 hops, but just-in-time delivery only asks whether the rate meets the demand. Both versions meet it at 1 and 2 hops and miss it from 3 hops on, so their on-time results are identical. The rate is limited by link loss, Bell-measurement success and memory readout loss, not by memory decoherence.

## Code layout

- `run_all.py` — entry point
- `config.yaml` — every parameter, with its source
- `src/config.py` — loads `config.yaml`, checks that every value is numeric, every physics parameter has a source and every design choice has a reason
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
