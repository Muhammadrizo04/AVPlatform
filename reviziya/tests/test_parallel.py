"""Parallel so'rovlar: ikki kishi bir vaqtda «Yakunlash» yoki «Ochiqqa qaytarish» bossa — farq bir marta yoziladi."""
import threading
from decimal import Decimal

import pytest
from django.db import connection

from reviziya.models import Reviziya
from reviziya.qollash import ochiqqa_qaytar, yakunla_va_yoz
from reviziya.servis import ReviziyaXato, reviziya_och
from vositalar.models import Bolim, Holat, Taqsimot, TaqsimotHarakat
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db(transaction=True)


def _parallel(amal, *argsets):
    """Har argumentlar to'plami alohida oqimda (alohida DB ulanishi), bir vaqtda boshlanadi."""
    tosiq = threading.Barrier(len(argsets))
    natijalar = [None] * len(argsets)

    def ish(i, args):
        try:
            tosiq.wait()
            amal(*args)
            natijalar[i] = "ok"
        except ReviziyaXato as e:
            natijalar[i] = e
        finally:
            connection.close()

    oqimlar = [threading.Thread(target=ish, args=(i, a)) for i, a in enumerate(argsets)]
    for o in oqimlar:
        o.start()
    for o in oqimlar:
        o.join()
    return natijalar


@pytest.fixture
def sozla(filial_yarat, foydalanuvchi):
    filial = filial_yarat("07")
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial, soni="10")
    qator(stol, filial, "10", bolim=a)
    rv = reviziya_och(filial, None, [foydalanuvchi("revizor")], [], foydalanuvchi("hisobchi"))
    return rv, stol, foydalanuvchi("hisobchi"), foydalanuvchi("hisobchi")


def _holatlar(av):
    return {t.holat: t.soni for t in Taqsimot.objects.filter(av=av) if t.soni}


def test_ikki_kishi_birdan_yakunlasa_bir_marta_yoziladi(sozla):
    rv, stol, h1, h2 = sozla
    natijalar = _parallel(yakunla_va_yoz, (rv, h1), (rv, h2))

    assert natijalar.count("ok") == 1
    assert sum(isinstance(n, ReviziyaXato) for n in natijalar) == 1
    assert TaqsimotHarakat.objects.filter(av=stol).count() == 1
    assert _holatlar(stol) == {Holat.TOPILMADI: Decimal("10")}
    assert Reviziya.objects.get(pk=rv.pk).holat == Reviziya.Holat.YAKUNLANGAN


def test_ikki_kishi_birdan_ochiqqa_qaytarsa_bir_marta_qaytadi(sozla):
    rv, stol, h1, h2 = sozla
    yakunla_va_yoz(rv, h1)
    natijalar = _parallel(ochiqqa_qaytar, (rv, h1), (rv, h2))

    assert natijalar.count("ok") == 1
    assert _holatlar(stol) == {Holat.ISHLATILMOQDA: Decimal("10")}
    assert Reviziya.objects.get(pk=rv.pk).holat == Reviziya.Holat.OCHIQ
