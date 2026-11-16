"""Tests for credit calculations."""

from credits import CreditCalculator, format_credits


def test_species_value():
    calc = CreditCalculator()
    assert calc.species_value("Stratum Tectonicas") == 19010800
    assert calc.species_value("Bacterium Cerbrus") == 1689800
    assert calc.species_value("Made Up Species") is None


def test_collection_value_only_when_complete():
    calc = CreditCalculator()
    assert calc.collection_value("Stratum Tectonicas", completed=False) is None
    assert calc.collection_value("Stratum Tectonicas", completed=True) == 19010800


def test_planet_value():
    calc = CreditCalculator()
    assert calc.planet_value([19010800, 1689800]) == 20700600
    assert calc.planet_value([None, 1689800]) == 1689800
    assert calc.planet_value([]) == 0


def test_first_footfall_not_guaranteed():
    calc = CreditCalculator()
    val = calc.first_footfall_value(19010800)
    assert val == 19010800 * 4


def test_format_credits():
    assert format_credits(None) == "Unknown"
    assert format_credits(19010800) == "19.0M CR"
    assert format_credits(1689800) == "1.7M CR"
    assert format_credits(500) == "500 CR"
