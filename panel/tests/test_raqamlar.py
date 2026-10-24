from decimal import Decimal

import pytest
from django.template import Context, Template

from panel.templatetags.raqamlar import pul, son

BO = " "  # mingliklar orasidagi bo'linmas bo'sh joy


@pytest.mark.parametrize(
    "qiymat, kutilgan",
    [
        (Decimal("1108.000"), f"1{BO}108"),
        (Decimal("571.900"), "571,9"),
        (Decimal("29.500"), "29,5"),
        (Decimal("0.125"), "0,125"),
        (Decimal("1234567"), f"1{BO}234{BO}567"),
        (Decimal("-1500.5"), f"-1{BO}500,5"),
        (0, "0"),
        (12, "12"),
        (None, ""),
        ("", ""),
        ("abc", "abc"),
    ],
)
def test_son(qiymat, kutilgan):
    assert son(qiymat) == kutilgan


@pytest.mark.parametrize(
    "qiymat, kutilgan",
    [
        (Decimal("3485037435.36"), f"3{BO}485{BO}037{BO}435,36"),
        (Decimal("5195850"), f"5{BO}195{BO}850,00"),
        (Decimal("0.005"), "0,01"),
        (Decimal("-25.5"), "-25,50"),
        (999, "999,00"),
        (None, ""),
        ("abc", "abc"),
    ],
)
def test_pul(qiymat, kutilgan):
    assert pul(qiymat) == kutilgan


def test_filtrlar_hamma_shablonda_yuklashsiz_ishlaydi():
    natija = Template("{{ a|son }} / {{ b|pul }}").render(Context({"a": Decimal("2000.000"), "b": Decimal("10")}))
    assert natija == f"2{BO}000 / 10,00"
