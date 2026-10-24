import uuid
from datetime import date
from decimal import Decimal

import pytest

from onec.models import AV, AVTuri
from vositalar.amortizatsiya import Amortizatsiya, dona_narxi, hisobla, oy_qosh, samarali_muddat
from vositalar.models import AVKartochka, AVTuriSozlama

D = Decimal
BUGUN = date(2026, 10, 17)


def test_chiziqli():
    natija = hisobla(D("12000000"), date(2024, 1, 15), 60, BUGUN)

    assert natija == Amortizatsiya(
        oylar=33, qoldiq_qiymat=D("5400000.00"), eskirish_foiz=D("55.00"), tugash_sanasi=date(2029, 1, 15)
    )


def test_toliq_oy_kun_boyicha():
    # 20-kun hali kelmagan: 33-oy to'lmagan.
    assert hisobla(D("12000000"), date(2024, 1, 20), 60, BUGUN).oylar == 32


def test_muddat_otgan_nol():
    natija = hisobla(D("1000"), date(2020, 1, 1), 12, BUGUN)

    assert natija.qoldiq_qiymat == D("0.00")
    assert natija.eskirish_foiz == D("100.00")
    assert natija.tugash_sanasi == date(2021, 1, 1)


def test_kelajakdagi_sana():
    natija = hisobla(D("1000"), date(2027, 1, 1), 12, BUGUN)

    assert natija.oylar == 0
    assert natija.qoldiq_qiymat == D("1000.00")
    assert natija.eskirish_foiz == D("0.00")


def test_yaxlitlash_yarim_yuqoriga():
    # 100 * (1 - 1/3) = 66.666... -> 66.67; eskirish 33.333... -> 33.33
    natija = hisobla(D("100"), date(2026, 9, 17), 3, BUGUN)

    assert natija.oylar == 1
    assert natija.qoldiq_qiymat == D("66.67")
    assert natija.eskirish_foiz == D("33.33")


@pytest.mark.parametrize(
    "ishga_tushgan, muddat",
    [(date(2024, 1, 15), None), (date(2024, 1, 15), 0), (None, 60), (None, None)],
)
def test_muddat_yoki_sana_yoq_none(ishga_tushgan, muddat):
    assert hisobla(D("1000"), ishga_tushgan, muddat, BUGUN) is None


def test_oy_qosh_oy_oxiriga_qirqiladi():
    assert oy_qosh(date(2024, 1, 31), 1) == date(2024, 2, 29)  # kabisa yili
    assert oy_qosh(date(2025, 1, 31), 1) == date(2025, 2, 28)
    assert oy_qosh(date(2026, 10, 17), 6) == date(2027, 4, 17)
    assert oy_qosh(date(2026, 10, 31), 4) == date(2027, 2, 28)


def test_dona_narxi():
    assert dona_narxi(D("500"), D("4")) == D("125")


def test_dona_narxi_nol_soni():
    assert dona_narxi(D("500"), D("0")) == 0
    assert dona_narxi(D("500"), D("-1")) == 0


@pytest.mark.django_db
def test_samarali_muddat_ustunligi():
    turi = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="Mebel")
    AVTuriSozlama.objects.create(av_turi=turi, xizmat_muddati_oy=60)
    av = AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol", turi=turi)
    kartochka = AVKartochka.objects.create(av=av, xizmat_muddati_oy=24)

    assert samarali_muddat(kartochka) == 24

    kartochka.xizmat_muddati_oy = None
    assert samarali_muddat(kartochka) == 60


@pytest.mark.django_db
def test_samarali_muddat_sozlamasiz_none():
    turi = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="Mebel")
    turli = AVKartochka.objects.create(
        av=AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol", turi=turi)
    )
    turisiz = AVKartochka.objects.create(av=AV.objects.create(ref_1c=uuid.uuid4(), kod="2", nomi="Stul"))

    assert samarali_muddat(turli) is None
    assert samarali_muddat(turisiz) is None
