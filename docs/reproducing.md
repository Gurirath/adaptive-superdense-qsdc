# Reproducing the results

This document describes how to regenerate every figure and number in `results/`, and how to check that the output matches the published files.

## Environment of the published results

| Item | Value |
| --- | --- |
| Python | 3.13.11 |
| Operating system | Windows 11 |
| Packages | The exact versions in `requirements-lock.txt` |
| Command | `python run_all.py` |
| Run time | About one minute |

The main packages in the lock file are numpy 2.5.4, scipy 1.18.1, pandas 3.0.6, scikit-learn 1.9.1, matplotlib 3.11.2, pyyaml 6.0.3, qiskit 2.5.2 and qiskit-aer 0.17.2. The file also pins their direct dependencies.

## Steps

1. Get the code and move into its folder.

   ```bash
   git clone https://github.com/Gurirath/adaptive-superdense-qsdc.git
   cd adaptive-superdense-qsdc
   ```

2. Create a virtual environment with Python 3.13 and activate it.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows, activate with `.venv\Scripts\activate`.

3. Install the pinned versions.

   ```bash
   pip install -r requirements-lock.txt
   ```

4. Run every simulation.

   ```bash
   python run_all.py
   ```

   This overwrites the files in `results/` with freshly computed ones.

5. Compare the new files with the published ones.

   ```bash
   git status --short results
   git diff --stat results
   ```

   On the same operating system as the published run, nothing is listed, which means every figure, CSV file and number was reproduced byte for byte. On a different operating system, `results/key_numbers.json` and `results/qiskit_validation.json` should still match exactly, values in the CSV files may differ in the last floating-point digit, and the PNG files will differ in bytes even though the plots look the same.

6. Run the tests.

   ```bash
   pytest
   ```

   All tests should pass. This takes about a minute and a half.

## What to expect in other environments

All random seeds are fixed in `config.yaml`, so a given environment always gives the same output. Different environments can give slightly different output, for three reasons.

- Numerical libraries change. Different versions of numpy, pandas and scikit-learn can produce different random streams or rounding. The attack-detection recalls are the most sensitive: they moved by up to 0.006 between two sets of library versions. Every other number in `results/key_numbers.json` was identical between those two sets.
- Image files differ. A different matplotlib version usually writes different PNG bytes even when the plot looks the same. Compare `results/key_numbers.json` and `results/data/*.csv`, not the images.
- The Qiskit sample differs. A different version of qiskit-aer can draw different random samples, so the values in `results/qiskit_validation.json` change within their sampling error. The agreement test allows for this.

The test suite checks identities and bounds, not stored numbers, so it passes in any supported environment. It has been run with the versions in `requirements-lock.txt` and with the lowest versions allowed by `requirements.txt`, both on Python 3.13. The workflow in `.github/workflows/tests.yml` runs it on Python 3.11, 3.12 and 3.13.

## Partial and quick runs

| Command | Use |
| --- | --- |
| `python run_all.py --only fig07` | Regenerate one figure. The rest of `results/key_numbers.json` is kept. |
| `python run_all.py --only fig05 fig06` | Regenerate several figures. |
| `python run_all.py --fast --out check` | A shorter run into a separate folder, for a quick check. Its numbers differ from the published ones because the simulations are shorter. |

Figures 5 and 6 are made together, as are 10 and 11, and 12 and 13, so naming one of a pair regenerates both.

## Changing a parameter

Edit the value in `config.yaml` and run `python run_all.py` again. Write numbers with an exponent as `1.0e-8`, not `1e-8`. The loader stops with an error if a value is not a number, if a physics parameter has no source, or if a design choice has no reason.

## Figures in the paper

The paper numbers its figures differently from the files, because its first two figures are diagrams that this code does not generate.

| Figure in the paper | File |
| --- | --- |
| 3 | `fig02_superdense_security.png` |
| 4 | `fig03_switch_rule.png` |
| 5 | `fig01_rate_vs_distance.png` |
| 6 | `fig04_crossover_sensitivity.png` |
| 7 | `fig05_attack_timeseries.png` |
| 8 | `fig06_detection_comparison.png` |
| 9 | `fig07_on_time_vs_hops.png` |
| 10 | `fig09_pool_sizing.png` |
| 11 | `fig08_pool_timeseries.png` |
| 12 | `fig14_finite_key.png` |
| 13 | `fig15_memory_needed.png` |
| 14 | `fig12_hybrid_bars.png` |
| 15 | `fig13_hybrid_timeseries.png` |
| 16 | `fig10_multicast_on_time.png` |
| 17 | `fig11_ghz_vs_bipartite.png` |
| 18 | `fig16_scheduling.png` |
| 19 | `fig17_design_space.png` |

`fig18_qiskit_validation.png` is an additional check that is not in the paper.

## Running on IBM hardware

`scripts/run_on_ibm_hardware.py` is optional and is not needed to reproduce anything in `results/`. See the README for how to use it.
