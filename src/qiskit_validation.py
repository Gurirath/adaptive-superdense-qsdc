import json
import numpy as np
from config import CFG
from core import werner_weights, qber_from_weights, chsh_from_weights
from transports import compose

try:
    import qiskit
    import qiskit_aer
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

V = CFG["experiments"]["fig18"]
ALICE, BOB = 0, 1
ENCODINGS = [(0, 0), (1, 0), (0, 1), (1, 1)]
ERROR_NAMES = ["no_error", "bit_flip", "phase_flip", "bit_and_phase_flip"]
CHSH_SETTINGS = [(0.0, np.pi / 4, 1), (0.0, -np.pi / 4, 1), (np.pi / 2, np.pi / 4, 1), (np.pi / 2, -np.pi / 4, -1)]


def pair_depolarizing(F):
    return 4 * (1 - F) / 3


def noise_model(F, return_noise):
    model = NoiseModel()
    if pair_depolarizing(F) > 0:
        model.add_quantum_error(depolarizing_error(pair_depolarizing(F), 1), "id", [BOB])
    if return_noise > 0:
        model.add_quantum_error(depolarizing_error(return_noise, 1), "id", [ALICE])
    return model


def bell_pair(noise_slots=True):
    qc = QuantumCircuit(2, 2)
    qc.h(ALICE)
    qc.cx(ALICE, BOB)
    if noise_slots:
        qc.id(BOB)
    return qc


def superdense_circuit(x, z, noise_slots=True):
    qc = bell_pair(noise_slots)
    if x:
        qc.x(ALICE)
    if z:
        qc.z(ALICE)
    if noise_slots:
        qc.id(ALICE)
    qc.cx(ALICE, BOB)
    qc.h(ALICE)
    qc.measure([ALICE, BOB], [0, 1])
    return qc


def qber_circuit(basis, noise_slots=True):
    qc = bell_pair(noise_slots)
    if basis == "x":
        qc.h(ALICE)
        qc.h(BOB)
    qc.measure([ALICE, BOB], [0, 1])
    return qc


def chsh_circuit(theta_alice, theta_bob, noise_slots=True):
    qc = bell_pair(noise_slots)
    qc.ry(-theta_alice, ALICE)
    qc.ry(-theta_bob, BOB)
    qc.measure([ALICE, BOB], [0, 1])
    return qc


def decoding_errors(counts_per_encoding):
    errors = np.zeros(4)
    for (x, z), counts in zip(ENCODINGS, counts_per_encoding):
        for bits, n in counts.items():
            z_seen, x_seen = int(bits[-1]), int(bits[-2])
            errors[(x_seen ^ x) + 2 * (z_seen ^ z)] += n
    return errors


def mismatches(counts):
    return sum(n for bits, n in counts.items() if bits[-1] != bits[-2])


def correlation(counts):
    total = sum(counts.values())
    return (total - 2 * mismatches(counts)) / total


def chsh_value(counts_per_setting):
    return sum(sign * correlation(c) for (_, _, sign), c in zip(CHSH_SETTINGS, counts_per_setting))


def all_circuits(noise_slots=True):
    return {
        "superdense": [superdense_circuit(x, z, noise_slots) for x, z in ENCODINGS],
        "qber": [qber_circuit("z", noise_slots), qber_circuit("x", noise_slots)],
        "chsh": [chsh_circuit(a, b, noise_slots) for a, b, _ in CHSH_SETTINGS],
    }


def simulate(circuits, F, return_noise, shots, seed):
    backend = AerSimulator(noise_model=noise_model(F, return_noise), seed_simulator=seed)
    result = backend.run(circuits, shots=shots).result()
    return [result.get_counts(i) for i in range(len(circuits))]


def row(F, quantity, analytic, measured, se):
    z = 0.0 if measured == analytic else (float("inf") if se == 0 else (measured - analytic) / se)
    return {"F": F, "quantity": quantity, "analytic": float(analytic), "qiskit": float(measured), "standard_error": float(se), "z_score": float(z)}


def binomial_se(p, n):
    return np.sqrt(max(p * (1 - p), 0.0) / n)


def validate(fidelities=V["fidelities"], shots=V["shots"], return_noise=V["return_noise"], seed=V["seed"]):
    rows = []
    circuits = all_circuits()
    for F in fidelities:
        p = werner_weights(F)
        sd = simulate(circuits["superdense"], F, return_noise, shots, seed)
        qb = simulate(circuits["qber"], F, 0.0, shots, seed + 1)
        ch = simulate(circuits["chsh"], F, 0.0, shots, seed + 2)
        n_decode = shots * len(ENCODINGS)
        measured = decoding_errors(sd) / n_decode
        expected = compose(p, return_noise)
        for name, e, m in zip(ERROR_NAMES, expected, measured):
            rows.append(row(F, f"decode_{name}", e, m, binomial_se(e, n_decode)))
        ez, ex = qber_from_weights(p)
        rows.append(row(F, "qber_z", ez, mismatches(qb[0]) / shots, binomial_se(ez, shots)))
        rows.append(row(F, "qber_x", ex, mismatches(qb[1]) / shots, binomial_se(ex, shots)))
        w = (4 * F - 1) / 3
        chsh_se = np.sqrt(sum(1 - (w * np.cos(a - b)) ** 2 for a, b, _ in CHSH_SETTINGS) / shots)
        rows.append(row(F, "chsh", chsh_from_weights(p), chsh_value(ch), chsh_se))
    return rows


def report(rows, shots=V["shots"], return_noise=V["return_noise"], seed=V["seed"]):
    return {
        "qiskit_version": qiskit.__version__,
        "qiskit_aer_version": qiskit_aer.__version__,
        "shots_per_circuit": shots,
        "return_noise": return_noise,
        "seed": seed,
        "sigma_bound": V["sigma_bound"],
        "largest_abs_z_score": max(abs(r["z_score"]) for r in rows),
        "all_within_bound": all(abs(r["z_score"]) <= V["sigma_bound"] for r in rows),
        "rows": rows,
    }


if __name__ == "__main__":
    if not AVAILABLE:
        raise SystemExit("Qiskit is not installed: pip install qiskit qiskit-aer")
    out = report(validate())
    for r in out["rows"]:
        print(f"F={r['F']:<5} {r['quantity']:<26} analytic={r['analytic']:.5f} qiskit={r['qiskit']:.5f} se={r['standard_error']:.5f} z={r['z_score']:+.2f}")
    print("largest |z|:", round(out["largest_abs_z_score"], 2), "| all within bound:", out["all_within_bound"])
    with open("out_qiskit_validation.json", "w") as fh:
        json.dump(out, fh, indent=2)
