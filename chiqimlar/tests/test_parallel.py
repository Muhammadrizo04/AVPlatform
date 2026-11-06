"""Parallel so'rovlar: bitta chiqimni ikki kishi bir vaqtda tasdiqlasa yoki tasdig'ini qaytarsa — amal bir marta bo'ladi."""
import threading

import pytest
from django.db import connection

from chiqimlar.models import ChiqimHujjat
from chiqimlar.servis import ChiqimXato, tasdiqla, tasdiqni_qaytar
from chiqimlar.tests.test_qaytarish import SON, boshlanish, muhit, ofisdan_tasdiqla  # noqa: F401 (fixture'lar)
from vositalar.models import Taqsimot, TaqsimotHarakat

pytestmark = pytest.mark.django_db(transaction=True)


def _parallel(*amallar):
    tosiq = threading.Barrier(len(amallar))
    natijalar = [None] * len(amallar)

    def ish(i, amal):
        try:
            tosiq.wait()
            amal()
            natijalar[i] = "ok"
        except ChiqimXato as e:
            natijalar[i] = e
        finally:
            connection.close()

    oqimlar = [threading.Thread(target=ish, args=(i, a)) for i, a in enumerate(amallar)]
    for o in oqimlar:
        o.start()
    for o in oqimlar:
        o.join()
    return natijalar


def test_ikki_kishi_birdan_tasdiqlasa_bir_marta_ayiriladi(muhit, foydalanuvchi):
    m = muhit
    qator = Taqsimot.objects.get(av=m["av"], bolim=m["ofis"])
    h2 = foydalanuvchi("hisobchi")

    def tasdiq(kim):
        return lambda: tasdiqla(m["c"], "sotildi", {qator.pk: SON("1")}, kim, kutilgan_soni=SON("1"))

    natijalar = _parallel(tasdiq(m["hisobchi"]), tasdiq(h2))

    assert natijalar.count("ok") == 1
    assert sum(isinstance(n, ChiqimXato) for n in natijalar) == 1
    assert Taqsimot.objects.get(pk=qator.pk).soni == SON("1")
    assert ChiqimHujjat.objects.get(pk=m["c"].pk).holat == ChiqimHujjat.Holat.TASDIQLANGAN


def test_ikki_kishi_birdan_qaytarsa_bir_marta_qaytadi(muhit, foydalanuvchi):
    m = muhit
    ofisdan_tasdiqla(m)
    qator = Taqsimot.objects.get(av=m["av"], bolim=m["ofis"])
    oldin = TaqsimotHarakat.objects.count()
    h2 = foydalanuvchi("hisobchi")

    natijalar = _parallel(lambda: tasdiqni_qaytar(m["c"], m["hisobchi"]), lambda: tasdiqni_qaytar(m["c"], h2))

    assert natijalar.count("ok") == 1
    assert Taqsimot.objects.get(pk=qator.pk).soni == SON("2")
    assert TaqsimotHarakat.objects.count() - oldin == 1
    assert ChiqimHujjat.objects.get(pk=m["c"].pk).holat == ChiqimHujjat.Holat.KUTILMOQDA
