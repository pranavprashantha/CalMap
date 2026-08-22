from decimal import Decimal

import pytest

from scripts.import_usda import build_portion_description, format_amount


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("1.000"), "1"),
        (Decimal("0.500"), "0.5"),
        (Decimal("2"), "2"),
        (None, ""),
    ],
)
def test_format_amount_strips_trailing_zeros(amount, expected):
    assert format_amount(amount) == expected


def test_portion_with_real_unit():
    assert build_portion_description(Decimal("1"), "cup", "", "") == "1 cup"


def test_portion_with_unit_and_modifier():
    assert (
        build_portion_description(Decimal("1"), "cup", "", "chopped") == "1 cup, chopped"
    )


def test_portion_without_unit_uses_modifier_text():
    """measure_unit_id 9999 ("undetermined") means the label lives in modifier."""
    assert (
        build_portion_description(Decimal("1"), "undetermined", "", "serving 1 roll with icing")
        == "serving 1 roll with icing"
    )


def test_portion_without_unit_keeps_non_unit_amount():
    assert (
        build_portion_description(Decimal("2"), "undetermined", "", "cookie") == "2 x cookie"
    )


def test_portion_falls_back_to_portion_description():
    assert build_portion_description(Decimal("1"), None, "1 medium", "") == "1 medium"


def test_portion_defaults_to_serving_when_nothing_is_given():
    assert build_portion_description(Decimal("1"), None, "", "") == "serving"


def test_fractional_amount_formats_readably():
    assert build_portion_description(Decimal("0.5"), "cup", "", "sliced") == "0.5 cup, sliced"
