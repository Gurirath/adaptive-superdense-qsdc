import numpy as np
import pytest

from core import BELL, bell_diag_purification, chsh_from_weights, ptrace, werner_weights

TOL = 1e-12
WEIGHTS = [werner_weights(F) for F in (0.25, 0.5, 0.82, 0.95, 1.0)] + [np.array([0.7, 0.2, 0.1, 0.0]), np.array([0.4, 0.3, 0.2, 0.1])]


def bell_diagonal_state(p):
    psi = bell_diag_purification(p)
    return ptrace(np.outer(psi, psi.conj()), [4, 4], [0])


def test_bell_states_are_orthonormal():
    gram = np.array([[np.vdot(a, b) for b in BELL] for a in BELL])
    assert np.allclose(gram, np.eye(4), atol=TOL)


@pytest.mark.parametrize("p", WEIGHTS)
def test_purification_is_normalised(p):
    psi = bell_diag_purification(p)
    assert np.vdot(psi, psi).real == pytest.approx(1.0, abs=TOL)


@pytest.mark.parametrize("p", WEIGHTS)
def test_bell_diagonal_state_has_unit_trace(p):
    assert np.trace(bell_diagonal_state(p)).real == pytest.approx(1.0, abs=TOL)


@pytest.mark.parametrize("p", WEIGHTS)
def test_bell_diagonal_state_is_positive_semidefinite(p):
    rho = bell_diagonal_state(p)
    assert np.allclose(rho, rho.conj().T, atol=TOL)
    assert np.linalg.eigvalsh(rho).min() >= -TOL


@pytest.mark.parametrize("p", WEIGHTS)
def test_bell_diagonal_state_has_the_requested_weights(p):
    rho = bell_diagonal_state(p)
    weights = [np.vdot(b, rho @ b).real for b in BELL]
    assert np.allclose(weights, p, atol=TOL)


def test_chsh_reaches_tsirelson_bound_at_unit_fidelity():
    assert chsh_from_weights(werner_weights(1.0)) == pytest.approx(2 * np.sqrt(2), abs=TOL)


@pytest.mark.parametrize("F", np.linspace(0.25, 0.5, 6))
def test_chsh_is_below_two_for_separable_werner_states(F):
    assert chsh_from_weights(werner_weights(F)) < 2
