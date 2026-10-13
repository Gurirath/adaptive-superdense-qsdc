import numpy as np
import pytest

from core import sdc_information, sdc_linear_optics, shannon, werner_weights
from transports import key_per_pair, sdc_per_pair

FIDELITIES = [0.82, 0.85, 0.9, 0.95, 0.99, 1.0]
RETURN_NOISE = [0.0, 0.02, 0.1, 0.3]


@pytest.mark.parametrize("F", FIDELITIES)
def test_superdense_rate_is_twice_key_rate_on_a_noiseless_return_leg(F):
    p = werner_weights(F)
    key = key_per_pair(p, "tomographic")
    assert key > 0
    assert sdc_per_pair(p, 0.0, "tomographic") == pytest.approx(2 * key, abs=1e-12)


@pytest.mark.parametrize("F", FIDELITIES)
def test_bob_receives_two_bits_minus_the_pair_entropy(F):
    p = werner_weights(F)
    assert sdc_information(p, 0.0)["I_bob"] == pytest.approx(2 - shannon(p), abs=1e-9)


@pytest.mark.parametrize("q", RETURN_NOISE)
@pytest.mark.parametrize("F", [0.25, 0.5, 0.7] + FIDELITIES)
def test_eve_holevo_information_is_bounded_by_the_pair_entropy(F, q):
    p = werner_weights(F)
    info = sdc_information(p, q)
    bound = shannon(p) + 1e-9
    assert info["chi_eve_passive"] <= bound
    assert info["chi_eve_intercept"] <= bound


@pytest.mark.parametrize("q", [0.0, 0.05, 0.3, 1.0])
@pytest.mark.parametrize("F", np.linspace(0.25, 1.0, 16))
def test_linear_optics_bell_measurement_carries_at_most_log2_three_bits(F, q):
    information, _ = sdc_linear_optics(werner_weights(F), q)
    assert information <= np.log2(3) + 1e-12


def test_linear_optics_bell_measurement_reaches_log2_three_bits_for_a_perfect_pair():
    information, _ = sdc_linear_optics(werner_weights(1.0), 0.0)
    assert information == pytest.approx(np.log2(3), abs=1e-12)
