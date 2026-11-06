"""Reviziya: paneldagi «joyida», progress, «Bo'limsiz» topilgan AV va dalolatnoma narxi."""
from decimal import Decimal as D

import pytest
from django.test import Client
from django.urls import reverse

from onec.models import AVQoldiq
from reviziya.pdf import _narxlar
from reviziya.qollash import yakunla_va_yoz
from reviziya.servis import progress, qayd_qosh, reviziya_och, xona_tugadi
from reviziya.solishtir import bolim_boyicha, solishtir
from vositalar.models import Bolim, Holat, Taqsimot
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db
ISH, TOP = Holat.ISHLATILMOQDA, Holat.TOPILMADI


@pytest.fixture
def f(filial_yarat):
    return filial_yarat("07")


@pytest.fixture
def his(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def rev(foydalanuvchi):
    return foydalanuvchi("revizor")


@pytest.fixture
def a(f):
    return Bolim.objects.create(filial=f, nomi="A")


def kirgan(u):
    c = Client()
    c.force_login(u)
    return c


def test_panelda_joyida_topilmadi_holatini_ishlatilmoqda_qiladi(f, a, his, rev):
    av = av_yarat(f)
    Taqsimot.objects.create(av=av, filial=f, bolim=a, holat=TOP, soni=D("1"))
    rv = reviziya_och(f, None, [rev], [], his)

    kirgan(his).post(reverse("reviziya:belgila", args=[rv.pk]), {"belgi": f"{av.pk}:{a.pk}:{TOP}=1"})
    yakunla_va_yoz(rv, his)

    assert Taqsimot.objects.get(av=av).holat == ISH


def test_progress_ortiqchani_sanamaydi(f, a, his, rev):
    kerak, begona = av_yarat(f, inv="K", soni="2"), av_yarat(f, inv="B", soni="2")
    qator(kerak, f, "2", bolim=a)
    rv = reviziya_och(f, a, [rev], [], his)
    qayd_qosh(rv, a, rev, av=begona, soni=D("2"))

    assert progress(rv) == (D("0"), D("2"))

    qayd_qosh(rv, a, rev, av=kerak, soni=D("5"))
    assert progress(rv) == (D("2"), D("2"))


def test_progress_boshqa_xonada_topilganni_butun_reviziyada_sanaydi(f, a, his, rev):
    b = Bolim.objects.create(filial=f, nomi="B")
    av = av_yarat(f)
    qator(av, f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, b, rev, av=av)

    assert progress(rv) == (D("1"), D("1"))
    assert progress(rv, bolim_id=a.pk) == (D("0"), D("1"))
    assert progress(rv, bolim_id=b.pk) == (D("0"), D("0"))


def test_bolimsizda_topilgan_kesimda_va_sahifada_korinadi(f, a, his, rev):
    av = av_yarat(f)
    qator(av, f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, None, rev, av=av)
    [q] = solishtir(rv)

    assert bolim_boyicha([q], "bolimsiz") == [q]

    xona_tugadi(rv, a, rev)
    yakunla_va_yoz(rv, his)
    html = kirgan(his).get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert "xona noma" in html
    assert Taqsimot.objects.get(av=av).bolim == a


def test_dalolatnoma_narxi_reviziya_ochilgandagi(f, a, his, rev):
    av = av_yarat(f, soni="3")  # 100 / 3
    qator(av, f, "3", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    AVQoldiq.objects.filter(av=av).update(summa=D("999"))

    narx = _narxlar(rv, solishtir(rv))[av.pk]

    assert (narx * 3).quantize(D("0.01")) == D("100.00")


def test_eski_reviziyada_joriy_narx(f, a, his, rev):
    av = av_yarat(f)
    qator(av, f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    rv.kutilganlar.update(dona_narxi=None)

    assert _narxlar(rv, solishtir(rv))[av.pk] == D("100")
