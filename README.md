# Adaptive superdense coding with outage-resilient key pools for secure one-to-one and one-to-many quantum communication

Simulation code and results for the paper of the same title by Gurirath Singh Khurana and Mohit Agrawal, School of Computer Science and Engineering, Vellore Institute of Technology.

## Summary

An entangled photon pair can protect a message in two ways. In key mode the two parties measure the pair to make a secret key and then encrypt with it. In superdense mode the sender encodes the message directly on her half of the pair and sends it back, which is quantum secure direct communication (QSDC) with no key at all. This repository models both on the same verified pairs and asks when each should be used, and how secrets can still arrive on time over several hops and to many receivers when links fail from time to time. It contains a density-matrix model of the two modes, a fibre link model, a telemetry-based attack detector, network simulations of outages with key pools, a one-to-many extension, and a scored sweep of 804 system designs. One command regenerates all 18 figures and every number quoted here.

## Key results

The numbers below are read from `results/key_numbers.json`, except the last two rows, which come from `results/data/design_space_sweep.csv` and `results/qiskit_validation.json`.

| Quantity | Baseline | Result | Figure |
| --- | --- | --- | --- |
| Secure bits per verified pair at fidelity 0.95 | Key mode: 0.634 | Superdense: 1.269, with Eve limited to 0.366 | fig02 |
| Switching threshold on return-leg transmission | none | 0.500 for every fidelity and for dimensions 2 to 16; 0.533 with 2% return noise | fig03 |
| Longest link on which superdense coding wins | Linear-optics Bell measurement: 0 km | 6 km with a 10 ms memory; 14 km with a perfect memory | fig01, fig04 |
| Secure rate at 50 km | Two-step QSDC: 71.0 kbit/s | Key mode and adaptive switch: 624 kbit/s | fig01 |
| Attack recall at a 1% false-alarm budget | Static error-rate threshold: 27.3% | Gradient-boosting detector: 99.2% | fig06 |
| Detector-blinding recall | Static error-rate threshold: 0% | Gradient-boosting detector: 100% | fig06 |
| On-time key delivery over 10 hops | Just-in-time: 37.9% | Key pool at every hop: 100% | fig07 |
| Missed requests in one hour on a 4-hop path | Just-in-time: 39.5% | Key pools: 0.28% | fig08 |
| Secure key rate at 150 km | 1-second blocks: 0 | 1-hour pooled blocks: 5,120 bit/s | fig14 |
| Hybrid protocol on a 1 km link | QSDC only: 91.6% on time | 99.6% on time with 92.0% of traffic sent without a key | fig12 |
| All 32 multicast receivers on time | Just-in-time: 4.6%; GHZ: 0% | Per-receiver pools: 94.4% | fig10 |
| Recommended practical design, out of 804 | Highest-security design: 0.6 bit/s at 50 km | Security score 0.865, 198 kbit/s at 50 km, 100% on time at 4 hops | fig17 |
| Qiskit check of the core physics | none | 28 of 28 comparisons within 3 standard errors | fig18 |

## Method overview

### Architecture

Every block of entangled pairs is treated as a resource that can be spent in one of two ways. The system has five stages.

1. Source. A source emits polarization-entangled pairs in the state |Phi+> at a fixed clock rate, with a small mean number of pairs per pulse. The pairs travel through fibre with loss and reach detectors with finite efficiency, dark counts and a small misalignment error.
2. Certification. A random sample of each block is measured to estimate the pair state. The model supports three levels: the two error rates of BBM92, full tomography of the Bell-diagonal weights, and a device-independent CHSH test.
3. Attack monitoring. Link telemetry (error rates in two bases, single counts, dark counts, double clicks, back-reflection and the CHSH value) is watched for attacks that a plain error-rate threshold would miss. A gradient-boosting classifier is compared with fixed thresholds.
4. Mode switch. A certified pair goes to superdense mode or to key mode. Superdense mode sends two bits per pair but the encoded photon must make the return trip, so its rate is cut by the return-leg transmission. Key mode needs no return trip. Comparing the two secure rates gives a threshold on the return-leg transmission: superdense mode wins only above it. With a noiseless return leg the threshold is exactly one half.
5. Delivery. Keys or messages are delivered one-to-one over several hops, or one-to-many from a hub. Links fail and recover at random. Keys made on demand arrive on time only if every hop is up at that moment, so the model adds classical key pools at each link, which fill while the link is up and are drawn on during outages.

### Hybrid protocol

Superdense mode has no key, which is its security advantage: nothing is stored that could later be stolen. For the same reason it cannot use a key pool, and it fails whenever the link is down. The hybrid protocol combines the two. For each time slot:

1. The block of pairs is certified by sampling, and the telemetry detector must raise no alarm. Otherwise the block is discarded.
2. If the link is up and the return-leg transmission is above the switching threshold, the message is sent by superdense coding. No key exists for it.
3. Pairs not needed for traffic are used in key mode, and the distilled key refills the pool.
4. If the link is up but the return-leg transmission is at or below the threshold, the block is used in key mode and the message is encrypted with a one-time pad from the pool.
5. If the link is down, the message is encrypted with a one-time pad from the pool, until the pool is empty.

On a 1 km link this keeps the 99.6% on-time delivery of a key pool while 92.0% of traffic never touches a stored key. The cost is that stored keys wait longer before use (204 s on average, against 86 s for a pool alone).

### What is simulated

| Part | Approach | Module |
| --- | --- | --- |
| Pair states, information and key rates | Exact density-matrix calculation on Bell-diagonal states | `src/core.py` |
| Fibre links and transport rates | Closed-form rate model for key mode, two-step QSDC, DL04 and ping-pong | `src/transports.py` |
| Attack detection | One synthetic telemetry sample per second for whole days, with modelled attack signatures | `src/detect.py` |
| Multi-hop delivery and pools | Time-stepped simulation with random outages | `src/deliver.py`, `src/pools.py` |
| One-to-many delivery | Time-stepped simulation of a hub with N receivers | `src/multicast.py` |
| Hybrid protocol and scheduling | Time-stepped simulation | `src/extend_net.py` |
| Finite-key effects | Closed-form finite-key rate | `src/extend_theory.py` |
| Design space | Enumeration and scoring of all valid combinations | `src/sweep.py` |
| Independent check | Qiskit circuits on the Aer simulator | `src/qiskit_validation.py` |

`docs/model.md` gives the equations used in each module.

## Quick start

Python 3.11, 3.12 or 3.13 is needed.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_all.py
pytest
```

On Windows, activate the environment with `.venv\Scripts\activate` instead of the `source` line.

`python run_all.py` takes about one minute and writes everything to `results/`:

| Output | Content |
| --- | --- |
| `results/fig01_*.png` to `results/fig18_*.png` | The figures, at 200 dpi |
| `results/key_numbers.json` | The headline numbers and a caption for each figure |
| `results/data/*.csv` | The data behind the figures |
| `results/qiskit_validation.json` | The Qiskit comparison |

Options:

| Command | Effect |
| --- | --- |
| `python run_all.py --fast` | Shorter simulations, for a quick check. The numbers differ slightly from the published ones. |
| `python run_all.py --only fig05` | Regenerate only the figures whose name contains the given text. Several names can be given. |
| `python run_all.py --out my_folder` | Write to another folder. |

`pytest` runs the test suite in about a minute and a half. A copy of all results is already in `results/`, so the figures can be viewed without running anything. `docs/reproducing.md` describes how to reproduce the published numbers exactly.

## Figures

The figure numbers here follow the file names. `docs/reproducing.md` maps them to the figure numbers in the paper.

### Figure 1: secure rate against distance

![Secure rate against fibre distance](results/fig01_rate_vs_distance.png)

Superdense coding beats key mode only below 6 km; at 50 km key mode gives 624 kbit/s against 71 kbit/s for two-step QSDC and 52 kbit/s for DL04.

### Figure 2: security of superdense coding

![Bits per entangled pair against fidelity](results/fig02_superdense_security.png)

Superdense coding gives twice the secure bits of key mode per verified pair (1.27 against 0.63 at fidelity 0.95), and Eve's information stays at or below the pair entropy H(p).

### Figure 3: switching rule

![Ratio of superdense to key-mode rate](results/fig03_switch_rule.png)

The ratio of the superdense rate to the key-mode rate crosses 1 at a return-leg transmission of 0.5 for every fidelity; 2% noise on the return leg moves the threshold to 0.533.

### Figure 4: crossover distance

![Largest distance at which superdense coding wins](results/fig04_crossover_sensitivity.png)

Superdense coding wins up to 6, 11 and 12 km for memory coherence times of 10 ms, 100 ms and 1 s, up to 14 km with a perfect memory, and nowhere with a 1 ms memory or a linear-optics Bell measurement.

### Figure 5: telemetry with attacks

![Link telemetry with attacks and alarms](results/fig05_attack_timeseries.png)

Ninety minutes of simulated telemetry containing all three attack types: the static error-rate alarm responds mainly to intercept-resend, while the classifier also responds to detector blinding and Trojan-horse probing.

### Figure 6: attack detection

![Attack recall by detector](results/fig06_detection_comparison.png)

At a 1% false-alarm budget the static error-rate threshold catches 27.3% of attack windows, thresholds on four monitors catch 73.4%, and the gradient-boosting detector catches 99.2%.

### Figure 7: on-time delivery against hops

![On-time key delivery against number of hops](results/fig07_on_time_vs_hops.png)

Just-in-time delivery through trusted relays follows 0.909^h, falling from 90.6% on one hop to 37.9% on ten, while a key pool at every hop delivers 100% on time.

### Figure 8: key pool over one hour

![Outages, pool level and misses on a 4-hop path](results/fig08_pool_timeseries.png)

On a 4-hop path the pool drains during outages and refills afterwards, missing 0.28% of requests against 39.5% for just-in-time delivery over the same outages.

### Figure 9: pool sizing

![On-time delivery against pool size](results/fig09_pool_sizing.png)

On 8 hops, on-time delivery rises from 47.4% with no pool to 97.8% at 50% load and 93.5% at 95% load with a pool of four mean outage lengths.

### Figure 10: multicast delivery

![Group key on time against number of receivers](results/fig10_multicast_on_time.png)

With 32 receivers, all receive the group key on time in 4.6% of rounds with just-in-time pairwise keys, never with GHZ conference keys, and in 94.4% of rounds with per-receiver pools.

### Figure 11: GHZ against pairwise keys

![Ratio of GHZ to pairwise group-key rate](results/fig11_ghz_vs_bipartite.png)

Behind a 50 km bottleneck, GHZ conference keys give a higher rate than pairwise keys only for short hub-to-receiver links and small groups.

### Figure 12: hybrid protocol

![Hybrid compared with its two components](results/fig12_hybrid_bars.png)

On a 1 km link the hybrid matches the 99.6% on-time delivery of a key pool while sending 92.0% of traffic without a key; QSDC alone reaches 91.6%, and stored keys in the hybrid are older when used (204 s against 86 s).

### Figure 13: hybrid protocol over time

![Hybrid protocol over 40 minutes](results/fig13_hybrid_timeseries.png)

Forty minutes of the hybrid: superdense transmission carries traffic while the link is up, and the pool covers the outages.

### Figure 14: finite-key effect of pooling

![Secure key rate against distance for different block sizes](results/fig14_finite_key.png)

At 100 km, 1-second blocks give 29.7 kbit/s and 1-hour pooled blocks give 53.1 kbit/s, against an asymptotic 59.5 kbit/s; at 150 km only pooled blocks give any key (5.12 kbit/s).

### Figure 15: memory needed by QSDC

![Secure bits per stored pair against memory coherence time](results/fig15_memory_needed.png)

Entangled pairs stored through a 30 s or 120 s outage lose their secure bits unless the memory coherence time is of the order of hundreds to a thousand seconds; a classical key pool has no such limit.

### Figure 16: multicast scheduling

![All 16 receivers on time against pool depth](results/fig16_scheduling.png)

For 16 receivers, deepening the pool from 10 s to 120 s of demand raises all-receivers-on-time from 40% to 97% with lowest-pool-first scheduling, while raising spare source capacity from 5% to 50% changes it by three points or less.

### Figure 17: design space

![All 804 designs by rate, security score and on-time delivery](results/fig17_design_space.png)

All 804 valid designs; the recommended practical design scores 0.865 for security, gives 198 kbit/s at 50 km and delivers 100% on time at 4 hops.

### Figure 18: Qiskit validation

![Qiskit simulation against the analytic model](results/fig18_qiskit_validation.png)

Decoding errors, error rates and CHSH values from Qiskit circuit simulation agree with the analytic model within 3 standard errors at every fidelity.

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

The file has 62 physics parameters, 37 design choices and 96 simulation settings. Eight physics parameters carry a published reference:

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
| `multicast`, `hybrid`, `scheduling` | One-to-many, QSDC and key-pool hybrid, and shared-source scheduling settings |
| `finite_key` | Finite-key security and block-size settings |
| `detection` | Synthetic telemetry, attack signatures and detector settings |
| `sweep` | Exposure weights and scoring settings of the design-space sweep |
| `experiments` | Grids, durations, seeds and displayed cases of each figure |
| `standalone` | Values used only when a module is run on its own |

The design-space sweep (fig17) does not store on-time delivery figures. It computes them when it runs, by calling the same delivery simulation as fig07 at 4 hops with the same duration and seeds, so the two always agree. Keyless transports use the just-in-time trusted-relay result. The one exception is delivery with a post-quantum fallback, which is on time by construction and is set to 1 in `config.yaml`.

To try a different value, edit it in `config.yaml` and re-run. Write numbers with an exponent as `1.0e-8`, not `1e-8`: the YAML reader treats the second form as text, and the loader stops with an error if it finds text where a number should be.

Mathematical constants stay in the code because they are part of the formulas, not choices: the factor of 10 in decibel conversion, the Werner-state and depolarising-channel coefficients, 0.5 as the largest possible error rate, and array dimensions. Plot styling in `src/figures.py` (figure sizes, colours, label positions) also stays in the code.

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

## Independent check with Qiskit

The core results come from our own density-matrix code in `src/core.py` and `src/transports.py`. `src/qiskit_validation.py` checks three of them a second way, by building the protocol as quantum circuits and running them on Qiskit's Aer simulator. The two calculations share no code beyond the final comparison.

The circuits are:

- The Bell pair |Φ+>, made with a Hadamard gate and a controlled-NOT.
- Superdense coding: Alice applies one of four Pauli operations to her half, and Bob decodes with a Bell measurement (controlled-NOT, Hadamard, then measure both qubits). All four encodings are run.
- Error rates: both halves of the pair are measured in the Z basis, then in the X basis.
- A Bell test: the four standard CHSH measurement settings, at angles 0 and 90 degrees for Alice and plus and minus 45 degrees for Bob.

Noise is added with a depolarizing noise model. A Werner pair of fidelity F is a perfect pair with one half depolarized with strength 4(1 − F)/3, so that is applied to Bob's half. For superdense coding, the encoded qubit is also depolarized with the return-leg noise set in `config.yaml` (2%). Every other gate is ideal.

Each circuit is run for 20000 shots, for F = 1.0, 0.98, 0.95 and 0.90. The comparisons are:

| Qiskit measurement | Compared with |
| --- | --- |
| How often Bob decodes with no error, a bit flip, a phase flip, or both | `compose()` in `src/transports.py` |
| Error rate in the Z basis and in the X basis | `qber_from_weights()` in `src/core.py` |
| CHSH value S | `chsh_from_weights()` in `src/core.py` |

That is 28 comparisons. All agree within 3 standard errors, and the largest difference is 1.6 standard errors. The standard error is the sampling error expected from the analytic value and the number of shots. The numbers are in `results/qiskit_validation.json` and plotted in `fig18_qiskit_validation.png`, whose error bars show 3 standard errors.

### Agreement table

Each cell gives the analytic value, the Qiskit value, and in brackets the difference in standard errors. These numbers are from `results/qiskit_validation.json`, produced with qiskit 2.5.2 and qiskit-aer 0.17.2. Decoding pools the four encodings, so it uses 80000 shots; the other rows use 20000 shots per circuit.

| Quantity | F = 1.0 | F = 0.98 | F = 0.95 | F = 0.9 |
| --- | --- | --- | --- | --- |
| Decoding: no error | 0.98500 / 0.98530 (+0.70) | 0.96540 / 0.96625 (+1.32) | 0.93600 / 0.93726 (+1.46) | 0.88700 / 0.88795 (+0.85) |
| Decoding: bit flip | 0.00500 / 0.00483 (-0.70) | 0.01153 / 0.01106 (-1.25) | 0.02133 / 0.02061 (-1.41) | 0.03767 / 0.03692 (-1.10) |
| Decoding: phase flip | 0.00500 / 0.00492 (-0.30) | 0.01153 / 0.01155 (+0.04) | 0.02133 / 0.02101 (-0.63) | 0.03767 / 0.03739 (-0.41) |
| Decoding: both | 0.00500 / 0.00495 (-0.20) | 0.01153 / 0.01114 (-1.05) | 0.02133 / 0.02111 (-0.43) | 0.03767 / 0.03774 (+0.11) |
| Error rate, Z basis | 0.00000 / 0.00000 (exact) | 0.01333 / 0.01220 (-1.40) | 0.03333 / 0.03135 (-1.56) | 0.06667 / 0.06445 (-1.26) |
| Error rate, X basis | 0.00000 / 0.00000 (exact) | 0.01333 / 0.01265 (-0.84) | 0.03333 / 0.03300 (-0.26) | 0.06667 / 0.06550 (-0.66) |
| CHSH value S | 2.82843 / 2.82920 (+0.08) | 2.75300 / 2.75140 (-0.16) | 2.63987 / 2.64240 (+0.24) | 2.45130 / 2.45220 (+0.08) |

The largest difference is 1.56 standard errors.

### Statistical bound used by the test

The automated test uses a slightly wider bound, for a statistical reason. With 28 comparisons, each held to 3 standard errors, there is about a 7% chance that at least one fails through sampling noise alone, even when the two calculations agree perfectly. The test therefore applies a Bonferroni correction: it fixes the chance of any false failure across all comparisons at 1%, and divides that between them. The bound for each comparison is z = norm.ppf(1 − 0.01 / (2n)), where n is the number of comparisons and the factor of 2 covers deviations in either direction. For n = 28 this gives 3.57 standard errors. The bound is computed from n, so it adjusts if fidelities or quantities are added, and the 1% rate is set in `config.yaml`.

`python run_all.py` produces fig18 with the other figures. If Qiskit is not installed, it prints a message and skips fig18; everything else still runs.

This check covers the pair state, the encoding and decoding, and the Bell test. It does not cover the security bounds, the fibre and rate model, or the network simulations, which have no circuit equivalent here.

### Running on real IBM hardware

`scripts/run_on_ibm_hardware.py` runs the same superdense coding and CHSH circuits on a real IBM Quantum device, without the simulated noise. It is not part of `run_all.py` or the tests, and it has not been run as part of this project.

```bash
pip install qiskit-ibm-runtime
export IBM_QUANTUM_TOKEN=your_token
python scripts/run_on_ibm_hardware.py
```

On Windows PowerShell, set the token with `$env:IBM_QUANTUM_TOKEN = "your_token"`. The script picks the least busy device unless `--backend` names one, and saves the counts, the decoding success rate and the CHSH value to `results/ibm_hardware.json`. Jobs wait in a queue and use your IBM Quantum allowance.

## Tests

The `tests/` folder checks the quantitative claims the results rely on. Run it from the project folder:

```bash
pytest
```

It takes about a minute and a half, nearly all of it the last test in the table.

| File | What it checks |
| --- | --- |
| `test_states.py` | The four Bell states are orthonormal. Bell-diagonal states have trace 1, are positive semidefinite and carry the requested weights. The CHSH value is 2√2 at fidelity 1 and below 2 for separable Werner states. |
| `test_superdense.py` | Superdense coding gives exactly twice the key-mode rate per pair on a noiseless return leg, for fidelities from 0.82 to 1. Eve's Holevo information, whether she only listens or intercepts the encoded qubit, never exceeds the pair entropy H(p). A linear-optics Bell measurement carries at most log2(3) bits. |
| `test_switching.py` | The switching threshold is 0.5 in dimensions 2, 3, 4, 8 and 16, and about 0.533 with 2% noise on the return leg. |
| `test_delivery.py` | Just-in-time on-time delivery over h hops matches (300/330)^h for every path length in fig07. |
| `test_qiskit_validation.py` | Every Qiskit measurement agrees with its analytic value within a Bonferroni-corrected bound, about 3.6 standard errors for 28 comparisons. Skipped if Qiskit is not installed. |
| `test_smoke.py` | `python run_all.py --fast` finishes without errors and writes every figure and the numbers file. |

Three points about how the tests are built:

- They check identities and bounds, not stored numbers. Results can differ in the last digits between library versions, so comparing against `results/key_numbers.json` would fail for reasons that have nothing to do with correctness.
- The factor of two between superdense coding and key mode is tested with tomographic certification, which is what the claim refers to. With BBM92 certification the two security bounds differ and the ratio is not exactly two.
- The delivery test allows a difference of 0.03, because the simulation is a finite random sample. The observed difference is at most 0.014.

The smoke test writes to a temporary folder, so running the tests never changes `results/`.

`.github/workflows/tests.yml` runs the same tests on every push, on Python 3.11, 3.12 and 3.13.

## Dependencies and reproducibility

There are two requirement files, for two purposes.

- `requirements.txt` is the flexible install. It gives the lowest version of each package that supports Python 3.11, 3.12 and 3.13, and lets pip choose anything newer. Use it to run or extend the code.
- `requirements-lock.txt` is the exact install. It pins every package used, and each of their direct dependencies, to the versions that produced the files in `results/`. Use it to reproduce the published figures and numbers exactly. Its versions need Python 3.13.

```bash
pip install -r requirements-lock.txt
python run_all.py
```

The published results were produced with Python 3.13.11 on Windows 11 and the versions in `requirements-lock.txt`. In that environment a second run reproduces every figure, CSV file and number byte for byte, because all random seeds are fixed in `config.yaml`. On a different operating system with the same package versions, `results/key_numbers.json` and `results/qiskit_validation.json` should still match exactly, values in the CSV files may differ in the last floating-point digit, and the PNG files will differ in bytes even though the plots look the same.

With other versions the results stay the same to the precision quoted in this README, but can differ in later digits. The attack-detection recalls are the most sensitive: they changed by up to 0.006 between two sets of library versions. The test suite passes with both the lowest versions in `requirements.txt` and the versions in `requirements-lock.txt`, on Python 3.13.

## Repository layout

| Path | Content |
| --- | --- |
| `run_all.py` | Entry point: runs every simulation and writes the figures and numbers |
| `config.yaml` | Every parameter, with its source or reason |
| `src/config.py` | Loads `config.yaml` and checks that every value is numeric, every physics parameter has a source and every design choice has a reason |
| `src/core.py` | Bell states, density matrices, entropies, Holevo information and key-rate formulas |
| `src/transports.py` | Fibre link model and the secure rate of each transport |
| `src/detect.py` | Synthetic telemetry, threshold detectors and the gradient-boosting detector |
| `src/deliver.py`, `src/pools.py` | Multi-hop delivery with outages, entanglement swapping and key pools |
| `src/multicast.py` | One-to-many group keys: pairwise links, GHZ states and per-receiver pools |
| `src/extend_net.py` | The QSDC and key-pool hybrid, and multicast scheduling |
| `src/extend_theory.py` | Finite-key rate and the switching threshold for qudits |
| `src/sweep.py` | The design-space sweep |
| `src/qiskit_validation.py` | The independent Qiskit check |
| `src/figures.py` | Builds every figure and the numbers file |
| `scripts/run_on_ibm_hardware.py` | Optional run on a real IBM Quantum device |
| `tests/` | The test suite |
| `results/` | Figures, numbers and data from the published run |
| `docs/model.md` | The equations used in each module |
| `docs/reproducing.md` | Step-by-step reproduction |
| `references.bib` | All references in BibTeX |
| `CITATION.cff` | Citation metadata |
| `SUMMARY.md` | One-page summary of the findings |

Each module in `src/` can also be run on its own, for example `cd src` and then `python transports.py`, to print its numbers.

## Limitations

- Simulation only. Every result comes from a model under the assumptions in `config.yaml`. Nothing here was measured on hardware.
- Most parameters are assumptions. Of 62 physics parameters, 8 carry a published reference and 54 are labelled as assumptions.
- Attack signatures are modelled, not measured. The telemetry and the effect of each attack on it are synthetic, so the detection results show that cross-channel features can separate these modelled attacks from benign drift. They are not the expected performance of a deployed detector.
- Sweep weights are heuristic. The security score of a design is one minus the mean of eight exposure scores, and those scores are judgement values between 0 and 1. The ranking depends on them.
- Outages are independent. Each link alternates between up and down with exponentially distributed durations. Correlated failures are not modelled.
- Asymptotic rates. The switching rule and the transport rates use asymptotic key rates. Finite-key effects are treated only in the comparison of pooled and just-in-time blocks.
- Certification matters for the factor of two. Superdense coding gives exactly twice the key-mode rate with tomographic certification. With BBM92 certification the two security bounds differ and the ratio is not exactly two.
- Scope of the Qiskit check. It covers the pair state, the encoding, the decoding and the Bell test. It does not cover the security bounds, the fibre and rate model, or the network simulations.
- The script for real IBM hardware has not been run.

## How to cite

If you use this code or its results, please cite the paper:

```bibtex
@misc{khurana2026adaptive,
  author = {Khurana, Gurirath Singh and Agrawal, Mohit},
  title  = {{Adaptive Superdense Coding with Outage-Resilient Key Pools for Secure One-to-One and One-to-Many Quantum Communication}},
  year   = {2026},
  note   = {Simulation code, version 1.0.0},
  url    = {https://github.com/Gurirath/adaptive-superdense-qsdc}
}
```

The code is at <https://github.com/Gurirath/adaptive-superdense-qsdc>. `CITATION.cff` holds the same information in a form that GitHub and reference managers can read.

## License

Released under the MIT License. See `LICENSE`.

## References

Every entry is in `references.bib`. Each DOI below was checked against the publisher's record. Entries 1 to 36 are the references of the paper, in the same order.

1. Bennett, C.H., Brassard, G. (1984). Quantum cryptography: Public key distribution and coin tossing. Proceedings of the IEEE International Conference on Computers, Systems and Signal Processing, 175-179. No DOI.
2. Ekert, A.K. (1991). Quantum cryptography based on Bell's theorem. Physical Review Letters 67, 661-663. [doi:10.1103/PhysRevLett.67.661](https://doi.org/10.1103/PhysRevLett.67.661)
3. Bennett, C.H., Brassard, G., Mermin, N.D. (1992). Quantum cryptography without Bell's theorem. Physical Review Letters 68, 557-559. [doi:10.1103/PhysRevLett.68.557](https://doi.org/10.1103/PhysRevLett.68.557)
4. Bennett, C.H., Wiesner, S.J. (1992). Communication via one- and two-particle operators on Einstein-Podolsky-Rosen states. Physical Review Letters 69, 2881-2884. [doi:10.1103/PhysRevLett.69.2881](https://doi.org/10.1103/PhysRevLett.69.2881)
5. Long, G.L., Liu, X.S. (2002). Theoretically efficient high-capacity quantum-key-distribution scheme. Physical Review A 65, 032302. [doi:10.1103/PhysRevA.65.032302](https://doi.org/10.1103/PhysRevA.65.032302)
6. Deng, F.G., Long, G.L., Liu, X.S. (2003). Two-step quantum direct communication protocol using the Einstein-Podolsky-Rosen pair block. Physical Review A 68, 042317. [doi:10.1103/PhysRevA.68.042317](https://doi.org/10.1103/PhysRevA.68.042317)
7. Boström, K., Felbinger, T. (2002). Deterministic Secure Direct Communication Using Entanglement. Physical Review Letters 89, 187902. [doi:10.1103/PhysRevLett.89.187902](https://doi.org/10.1103/PhysRevLett.89.187902)
8. Wójcik, A. (2003). Eavesdropping on the "Ping-Pong" Quantum Communication Protocol. Physical Review Letters 90, 157901. [doi:10.1103/PhysRevLett.90.157901](https://doi.org/10.1103/PhysRevLett.90.157901)
9. Zhang, Z. (2004). Correct mutual information, quantum bit error rate and secure transmission efficiency in Wojcik's eavesdropping scheme on ping-pong protocol. arXiv:quant-ph/0402099. <https://arxiv.org/abs/quant-ph/0402099>
10. Deng, F.G., Long, G.L. (2004). Secure direct communication with a quantum one-time pad. Physical Review A 69, 052319. [doi:10.1103/PhysRevA.69.052319](https://doi.org/10.1103/PhysRevA.69.052319)
11. Zhang, Z.j., Li, Y., Man, Z.x. (2005). Improved Wójcik's eavesdropping attack on ping-pong protocol without eavesdropping-induced channel loss. Physics Letters A 341, 385-389. [doi:10.1016/j.physleta.2005.05.023](https://doi.org/10.1016/j.physleta.2005.05.023)
12. Zhou, L., Sheng, Y.B., Long, G.L. (2020). Device-independent quantum secure direct communication against collective attacks. Science Bulletin 65, 12-20. [doi:10.1016/j.scib.2019.10.025](https://doi.org/10.1016/j.scib.2019.10.025)
13. Das, N., Basu, S., Paul, G., Rao, V.S. (2024). User-Authenticated Device-Independent Quantum Secure Direct Communication Protocol. 2024 IEEE 37th International System-on-Chip Conference (SOCC), 1-6. [doi:10.1109/SOCC62300.2024.10737816](https://doi.org/10.1109/SOCC62300.2024.10737816)
14. Hu, J.Y. et al. (2016). Experimental quantum secure direct communication with single photons. Light: Science & Applications 5, e16144. [doi:10.1038/lsa.2016.144](https://doi.org/10.1038/lsa.2016.144)
15. Zhang, W., Ding, D.S., Sheng, Y.B., Zhou, L., Shi, B.S., Guo, G.C. (2017). Quantum Secure Direct Communication with Quantum Memory. Physical Review Letters 118, 220501. [doi:10.1103/PhysRevLett.118.220501](https://doi.org/10.1103/PhysRevLett.118.220501)
16. Zhang, H., Sun, Z., Qi, R., Yin, L., Long, G.L., Lu, J. (2022). Realization of quantum secure direct communication over 100 km fiber with time-bin and phase quantum states. Light: Science & Applications 11, 83. [doi:10.1038/s41377-022-00769-w](https://doi.org/10.1038/s41377-022-00769-w)
17. Qi, Z., Li, Y., Huang, Y., Feng, J., Zheng, Y., Chen, X. (2021). A 15-user quantum secure direct communication network. Light: Science & Applications 10, 183. [doi:10.1038/s41377-021-00634-2](https://doi.org/10.1038/s41377-021-00634-2)
18. Yang, Y., Li, Y., Li, H., Wu, C., Zheng, Y., Chen, X. (2025). A 300-km fully-connected quantum secure direct communication network. Science Bulletin 70, 1445-1451. [doi:10.1016/j.scib.2025.02.038](https://doi.org/10.1016/j.scib.2025.02.038)
19. Yin, J. et al. (2020). Entanglement-based secure quantum cryptography over 1,120 kilometres. Nature 582, 501-505. [doi:10.1038/s41586-020-2401-y](https://doi.org/10.1038/s41586-020-2401-y)
20. Patra, A., Gupta, R., Das, T., Sen(De), A. (2024). Dimensional advantage in secure information trading via the noisy dense-coding protocol. Physical Review A 110, 032419. [doi:10.1103/PhysRevA.110.032419](https://doi.org/10.1103/PhysRevA.110.032419)
21. Clauser, J.F., Horne, M.A., Shimony, A., Holt, R.A. (1969). Proposed Experiment to Test Local Hidden-Variable Theories. Physical Review Letters 23, 880-884. [doi:10.1103/PhysRevLett.23.880](https://doi.org/10.1103/PhysRevLett.23.880)
22. Devetak, I., Winter, A. (2005). Distillation of secret key and entanglement from quantum states. Proceedings of the Royal Society A: Mathematical, Physical and Engineering Sciences 461, 207-235. [doi:10.1098/rspa.2004.1372](https://doi.org/10.1098/rspa.2004.1372)
23. Holevo, A.S. (1973). Bounds for the quantity of information transmitted by a quantum communication channel. Problems of Information Transmission 9, 177-183. No DOI.
24. Lütkenhaus, N., Calsamiglia, J., Suominen, K.A. (1999). Bell measurements for teleportation. Physical Review A 59, 3295-3300. [doi:10.1103/PhysRevA.59.3295](https://doi.org/10.1103/PhysRevA.59.3295)
25. Lo, H.K., Curty, M., Qi, B. (2012). Measurement-Device-Independent Quantum Key Distribution. Physical Review Letters 108, 130503. [doi:10.1103/PhysRevLett.108.130503](https://doi.org/10.1103/PhysRevLett.108.130503)
26. Lydersen, L., Wiechers, C., Wittmann, C., Elser, D., Skaar, J., Makarov, V. (2010). Hacking commercial quantum cryptography systems by tailored bright illumination. Nature Photonics 4, 686-689. [doi:10.1038/nphoton.2010.214](https://doi.org/10.1038/nphoton.2010.214)
27. Gisin, N., Fasel, S., Kraus, B., Zbinden, H., Ribordy, G. (2006). Trojan-horse attacks on quantum-key-distribution systems. Physical Review A 73, 022320. [doi:10.1103/PhysRevA.73.022320](https://doi.org/10.1103/PhysRevA.73.022320)
28. Tomamichel, M., Lim, C.C.W., Gisin, N., Renner, R. (2012). Tight finite-key analysis for quantum cryptography. Nature Communications 3, 634. [doi:10.1038/ncomms1631](https://doi.org/10.1038/ncomms1631)
29. Mehić, M. et al. (2020). A Novel Approach to Quality-of-Service Provisioning in Trusted Relay Quantum Key Distribution Networks. IEEE/ACM Transactions on Networking 28, 168-181. [doi:10.1109/TNET.2019.2956079](https://doi.org/10.1109/TNET.2019.2956079)
30. Epping, M., Kampermann, H., Macchiavello, C., Bruß, D. (2017). Multi-partite entanglement can speed up quantum key distribution in networks. New Journal of Physics 19, 093012. [doi:10.1088/1367-2630/aa8487](https://doi.org/10.1088/1367-2630/aa8487)
31. Pirandola, S., Laurenza, R., Ottaviani, C., Banchi, L. (2017). Fundamental limits of repeaterless quantum communications. Nature Communications 8, 15043. [doi:10.1038/ncomms15043](https://doi.org/10.1038/ncomms15043)
32. Wegman, M.N., Carter, J. (1981). New hash functions and their use in authentication and set equality. Journal of Computer and System Sciences 22, 265-279. [doi:10.1016/0022-0000(81)90033-7](https://doi.org/10.1016/0022-0000(81)90033-7)
33. Gupta, S. (2026). Physics-aware temporal feature engineering for eavesdropping detection in BBM92 quantum key distribution. IACR Cryptology ePrint Archive, Paper 2026/1282. <https://eprint.iacr.org/2026/1282>
34. Scarani, V., Bechmann-Pasquinucci, H., Cerf, N.J., Dušek, M., Lütkenhaus, N., Peev, M. (2009). The security of practical quantum key distribution. Reviews of Modern Physics 81, 1301-1350. [doi:10.1103/RevModPhys.81.1301](https://doi.org/10.1103/RevModPhys.81.1301)
35. Gisin, N., Ribordy, G., Tittel, W., Zbinden, H. (2002). Quantum cryptography. Reviews of Modern Physics 74, 145-195. [doi:10.1103/RevModPhys.74.145](https://doi.org/10.1103/RevModPhys.74.145)
36. Salvail, L., Peev, M., Diamanti, E., Alléaume, R., Lütkenhaus, N., Länger, T. (2010). Security of trusted repeater quantum key distribution networks. Journal of Computer Security 18, 61-87. [doi:10.3233/JCS-2010-0373](https://doi.org/10.3233/JCS-2010-0373)

Additional references for parameter values and formulas in `config.yaml`:

37. Calsamiglia, J., Lütkenhaus, N. (2001). Maximum efficiency of a linear-optical Bell-state analyzer. Applied Physics B 72, 67-71. [doi:10.1007/s003400000484](https://doi.org/10.1007/s003400000484)
38. Scarani, V., Renner, R. (2008). Quantum cryptography with finite resources: Unconditional security bound for discrete-variable protocols with one-way postprocessing. Physical Review Letters 100, 200501. [doi:10.1103/PhysRevLett.100.200501](https://doi.org/10.1103/PhysRevLett.100.200501)
39. Lim, C.C.W., Curty, M., Walenta, N., Xu, F., Zbinden, H. (2014). Concise security bounds for practical decoy-state quantum key distribution. Physical Review A 89, 022307. [doi:10.1103/PhysRevA.89.022307](https://doi.org/10.1103/PhysRevA.89.022307)
40. Marsili, F. et al. (2013). Detecting single infrared photons with 93% system efficiency. Nature Photonics 7, 210-214. [doi:10.1038/nphoton.2013.13](https://doi.org/10.1038/nphoton.2013.13)
41. Wang, Y. et al. (2019). Efficient quantum memory for single-photon polarization qubits. Nature Photonics 13, 346-351. [doi:10.1038/s41566-019-0368-8](https://doi.org/10.1038/s41566-019-0368-8)
42. Grasselli, F., Curty, M. (2019). Practical decoy-state method for twin-field quantum key distribution. New Journal of Physics 21, 073001. [doi:10.1088/1367-2630/ab2b00](https://doi.org/10.1088/1367-2630/ab2b00)
43. Sangouard, N., Simon, C., de Riedmatten, H., Gisin, N. (2011). Quantum repeaters based on atomic ensembles and linear optics. Reviews of Modern Physics 83, 33-80. [doi:10.1103/RevModPhys.83.33](https://doi.org/10.1103/RevModPhys.83.33)
