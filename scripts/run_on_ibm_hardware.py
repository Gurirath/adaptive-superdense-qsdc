import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np

import qiskit_validation as qv


def main():
    ap = argparse.ArgumentParser(description="Run the CHSH and superdense coding circuits on a real IBM Quantum backend")
    ap.add_argument("--backend", default=os.environ.get("IBM_QUANTUM_BACKEND"), help="backend name; default is the least busy real device")
    ap.add_argument("--shots", type=int, default=qv.V["shots"])
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "ibm_hardware.json"))
    a = ap.parse_args()

    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        raise SystemExit("Set the IBM_QUANTUM_TOKEN environment variable to your IBM Quantum API token")
    if not qv.AVAILABLE:
        raise SystemExit("Qiskit is not installed: pip install qiskit qiskit-aer")
    try:
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    except ImportError:
        raise SystemExit("The IBM runtime client is not installed: pip install qiskit-ibm-runtime")

    account = {"channel": os.environ.get("IBM_QUANTUM_CHANNEL", "ibm_quantum_platform"), "token": token}
    if os.environ.get("IBM_QUANTUM_INSTANCE"):
        account["instance"] = os.environ["IBM_QUANTUM_INSTANCE"]
    service = QiskitRuntimeService(**account)
    backend = service.backend(a.backend) if a.backend else service.least_busy(operational=True, simulator=False, min_num_qubits=2)
    print(f"backend: {backend.name}")

    groups = qv.all_circuits(noise_slots=False)
    names = [(g, i) for g in ("superdense", "chsh") for i in range(len(groups[g]))]
    circuits = [groups[g][i] for g, i in names]
    isa = generate_preset_pass_manager(backend=backend, optimization_level=1).run(circuits)
    job = SamplerV2(mode=backend).run(isa, shots=a.shots)
    print(f"job: {job.job_id()} (waiting for the result)")
    result = job.result()
    counts = {}
    for (g, i), pub in zip(names, result):
        counts.setdefault(g, []).append(pub.data.c.get_counts())

    n_decode = a.shots * len(qv.ENCODINGS)
    decode = qv.decoding_errors(counts["superdense"]) / n_decode
    correlations = [qv.correlation(c) for c in counts["chsh"]]
    s = qv.chsh_value(counts["chsh"])
    s_se = float(np.sqrt(sum(1 - e ** 2 for e in correlations) / a.shots))
    out = {
        "backend": backend.name,
        "job_id": job.job_id(),
        "shots_per_circuit": a.shots,
        "superdense_decoding": {name: float(v) for name, v in zip(qv.ERROR_NAMES, decode)},
        "superdense_success_probability": float(decode[0]),
        "chsh_correlations": [float(e) for e in correlations],
        "chsh_value": float(s),
        "chsh_standard_error": s_se,
        "chsh_violates_classical_limit": bool(s - 2 > 3 * s_se),
        "raw_counts": counts,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"superdense decoding: {out['superdense_decoding']}")
    print(f"CHSH S = {s:.4f} +/- {s_se:.4f} (classical limit 2, quantum limit {2 * np.sqrt(2):.4f})")
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()
