"""Kartochka: majburiy maydon boshqa maydonni saqlatishga xalaqit bermaydi, tozalangan sana qaytmaydi; oy oxiri amortizatsiyasi."""
import uuid
from datetime import date
from decimal import Decimal as D

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from onec.models import AVTuri, Harakat1C
from vositalar.amortizatsiya import hisobla
from vositalar.models import AVKartochka, AVTuriSozlama
from vositalar.moslash import moslashtir
from vositalar.tests.test_bayroqlar import av_yarat
from vositalar.views import kartochka_saqla

pytestmark = pytest.mark.django_db


@pytest.fixture
def f(filial_yarat):
    return filial_yarat("07")


@pytest.fixture
def his(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def k(f):
    """Majburiy «seriya» va ixtiyoriy «rang» maydonli turdagi AV kartochkasi; ikkalasi ham hali bo'sh."""
    tur = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="T")
    AVTuriSozlama.objects.create(av_turi=tur, maydonlar=[
        {"kalit": "seriya", "nomi": "Seriya", "tip": "matn", "majburiy": True},
        {"kalit": "rang", "nomi": "Rang", "tip": "matn"},
    ])
    return AVKartochka.objects.create(av=av_yarat(f, turi=tur))


def test_ozgarmagan_qoshimcha_izoh_saqlashni_toxtatmaydi(k, his):
    kartochka_saqla(k, {"izoh": "yangi", "qoshimcha": {"seriya": "", "rang": ""}}, k.versiya, his)

    k.refresh_from_db()
    assert k.izoh == "yangi"


def test_qoshimcha_ozgarsa_majburiy_tekshiriladi(k, his):
    with pytest.raises(ValidationError):
        kartochka_saqla(k, {"qoshimcha": {"seriya": "", "rang": "qora"}}, k.versiya, his)


def test_majburiy_qiymatni_ochirib_bolmaydi(k, his):
    kartochka_saqla(k, {"qoshimcha": {"seriya": "S1", "rang": ""}}, k.versiya, his)

    with pytest.raises(ValidationError):
        kartochka_saqla(k, {"qoshimcha": {"seriya": "", "rang": ""}}, k.versiya, his)


def kirim(av, f):
    Harakat1C.objects.create(
        sana=timezone.now(), hujjat_turi="ПоступлениеОС", hujjat_ref=uuid.uuid4(), av=av, filial=f, vid="kirim", soni=1,
        summa=1,
    )


def test_tozalangan_sana_sinxronda_qaytmaydi(f, his):
    av = av_yarat(f)
    k = AVKartochka.objects.create(av=av, ishga_tushgan_sana=date(2020, 1, 1))
    kirim(av, f)
    kartochka_saqla(k, {"ishga_tushgan_sana": ""}, k.versiya, his)

    moslashtir()

    k.refresh_from_db()
    assert k.ishga_tushgan_sana is None


def test_bosh_sana_birinchi_kirimdan_toladi(f):
    av = av_yarat(f)
    k = AVKartochka.objects.create(av=av)
    kirim(av, f)

    moslashtir()

    k.refresh_from_db()
    assert k.ishga_tushgan_sana == timezone.localdate()


@pytest.mark.parametrize("bugun, oylar, qoldiq", [
    (date(2026, 2, 27), 5, "200.00"),
    (date(2026, 2, 28), 6, "0.00"),  # 31-avgust + 6 oy = 28-fevral: muddat tugadi
])
def test_oy_oxiri_tugash_sanasi_bilan_mos(bugun, oylar, qoldiq):
    a = hisobla(D("1200"), date(2025, 8, 31), 6, bugun)

    assert (a.oylar, a.qoldiq_qiymat) == (oylar, D(qoldiq))


def test_oddiy_oy_hisobi_ozgarmaydi():
    assert hisobla(D("1200"), date(2026, 1, 15), 12, date(2026, 3, 14)).oylar == 1
    assert hisobla(D("1200"), date(2026, 1, 15), 12, date(2026, 3, 15)).oylar == 2
