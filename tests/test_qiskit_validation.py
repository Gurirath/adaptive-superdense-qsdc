import pytest

pytest.importorskip("qiskit")
pytest.importorskip("qiskit_aer")

from config import CFG
from scipy.stats import norm

from qiskit_validation import ERROR_NAMES, bonferroni_bound, validate

V = CFG["experiments"]["fig18"]
QUANTITIES = [f"decode_{name}" for name in ERROR_NAMES] + ["qber_z", "qber_x", "chsh"]
N_COMPARISONS = len(V["fidelities"]) * len(QUANTITIES)


@pytest.fixture(scope="module")
def rows():
    return {(r["F"], r["quantity"]): r for r in validate()}


def test_every_fidelity_and_quantity_is_reported(rows):
    assert set(rows) == {(F, q) for F in V["fidelities"] for q in QUANTITIES}


def test_at_least_twenty_thousand_shots_per_circuit():
    assert V["shots"] >= 20000


def test_bound_is_computed_from_the_number_of_comparisons(rows):
    assert len(rows) == N_COMPARISONS
    bound = bonferroni_bound(len(rows))
    assert bound == pytest.approx(norm.ppf(1 - V["family_wise_error_rate"] / (2 * len(rows))), abs=1e-12)
    assert 2 * len(rows) * norm.sf(bound) == pytest.approx(V["family_wise_error_rate"], rel=1e-9)
    assert bonferroni_bound(2 * len(rows)) > bound


@pytest.mark.parametrize("quantity", QUANTITIES)
@pytest.mark.parametrize("F", V["fidelities"])
def test_qiskit_agrees_with_the_analytic_value(rows, F, quantity):
    r = rows[(F, quantity)]
    if r["standard_error"] == 0:
        assert r["qiskit"] == r["analytic"]
    else:
        assert abs(r["qiskit"] - r["analytic"]) <= bonferroni_bound(len(rows)) * r["standard_error"]


def test_decoding_error_probabilities_sum_to_one(rows):
    for F in V["fidelities"]:
        assert sum(rows[(F, f"decode_{name}")]["qiskit"] for name in ERROR_NAMES) == pytest.approx(1.0, abs=1e-12)
