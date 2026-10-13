import pytest

from core import werner_weights
from extend_theory import switch_threshold_qudit
from transports import switch_threshold_eta


@pytest.mark.parametrize("F", [0.9, 0.95, 0.99])
@pytest.mark.parametrize("d", [2, 3, 4, 8, 16])
def test_switching_threshold_is_one_half_in_every_dimension(d, F):
    threshold, key, sdc = switch_threshold_qudit(d, F)
    assert key > 0 and sdc > 0
    assert threshold == pytest.approx(0.5, abs=1e-12)


@pytest.mark.parametrize("F", [0.85, 0.9, 0.95, 0.99])
def test_qubit_switching_threshold_is_one_half_without_return_noise(F):
    assert switch_threshold_eta(werner_weights(F), 0.0) == pytest.approx(0.5, abs=1e-12)


def test_switching_threshold_with_two_percent_return_noise():
    assert switch_threshold_eta(werner_weights(0.95), 0.02) == pytest.approx(0.533, abs=1e-3)


def test_return_noise_raises_the_switching_threshold():
    p = werner_weights(0.95)
    thresholds = [switch_threshold_eta(p, q) for q in (0.0, 0.01, 0.02, 0.05)]
    assert thresholds == sorted(thresholds)
    assert thresholds[-1] > thresholds[0]
