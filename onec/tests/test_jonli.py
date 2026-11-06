"""Jonli sinov: `.env` dagi TestClaude'ga haqiqiy `sinxronla()`.

Standart o'tkazib yuboriladi (pytest.ini: `-m "not jonli"`). Ishga tushirish: `pytest -m jonli -q`.
ONEC_URL / ONEC_LOGIN / ONEC_PAROL muhitdan yoki .env dan olinadi (settings .env ni o'qiydi).
"""
import pytest
from django.conf import settings

from onec.client import OneCClient
from onec.models import AV, AVQoldiq, SinxronJurnal
from onec.sinxron import sinxronla
from vositalar.moslash import farq

pytestmark = [pytest.mark.jonli, pytest.mark.django_db(transaction=True)]


def test_haqiqiy_sinxron():
    if not (settings.ONEC_URL and settings.ONEC_LOGIN and settings.ONEC_PAROL):
        pytest.skip("ONEC_URL/ONEC_LOGIN/ONEC_PAROL sozlanmagan (.env)")

    jurnal = sinxronla(OneCClient.settingsdan(), toliq=True)
    assert jurnal.natija == SinxronJurnal.Natija.OK, jurnal.xato_matni

    assert AV.objects.count() > 0

    # Har (AV, filial) uchun: taqsimot 1C qoldig'iga teng (farq == 0) yoki «mos emas» (farq < 0) holatida.
    # farq > 0 (taqsimlanmagan qator yo'q) — moslash buzilgani.
    juftlar = AVQoldiq.objects.values_list("av_id", "filial_id").distinct()
    assert juftlar
    for av_id, filial_id in juftlar:
        av = AV.objects.get(pk=av_id)
        assert farq(av, filial_id) <= 0, f"AV {av.kod}: taqsimlanmagan qoldiq qoldi"
