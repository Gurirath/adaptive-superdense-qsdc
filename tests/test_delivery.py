import pytest

from config import CFG, availability
from deliver import mean_on_time

TOLERANCE = 0.03
FIG07 = CFG["experiments"]["fig07"]


def test_link_availability_is_three_hundred_over_three_hundred_thirty():
    assert availability() == pytest.approx(300 / 330, abs=1e-15)


@pytest.mark.parametrize("hops", FIG07["hops"])
def test_just_in_time_on_time_follows_availability_to_the_power_of_hops(hops):
    simulated = mean_on_time(hops, "jit_trusted_relay", FIG07["duration_s"]["full"])
    assert simulated == pytest.approx((300 / 330) ** hops, abs=TOLERANCE)
