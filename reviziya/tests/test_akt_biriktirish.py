"""Reviziyada Javobgar shaxsga biriktirish: akt yakunlashga ergashadi, biriktirish faqat shu xonadagi donani oladi."""
from decimal import Decimal as D

import pytest
from django.test import Client
from django.urls import reverse

from mol.models import MolAkt, MolAktQator
from mol.servis import akt_tasdiqla, qoralamaga_qosh
from reviziya.qollash import ochiqqa_qaytar, yakunla_va_yoz
from reviziya.servis import qayd_qosh, reviziya_och
from vositalar.models import Bolim, Holat, Taqsimot
from vositalar.tests.test_bayroqlar import av_yarat, qator, xodim

pytestmark = pytest.mark.django_db
ISH, NOSOZ, TOP = Holat.ISHLATILMOQDA, Holat.NOSOZ, Holat.TOPILMADI


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
def ab(f):
    return Bolim.objects.create(filial=f, nomi="A"), Bolim.objects.create(filial=f, nomi="B")


def akt_qatorlari():
    return sorted((q.bolim_id or 0, q.holat, q.soni) for q in MolAktQator.objects.all())


def akt(rv, top, qabul, t, rev, soni=None):
    return qoralamaga_qosh(top, qabul, [(t, soni or t.soni)], rev, rv.akt_izohi)[0]


def test_boshqa_xonada_topilgan_av_akti_tasdiqlanadi(f, his, rev, ab):
    a, b = ab
    eski, yangi = xodim(), xodim()
    av = av_yarat(f)
    t = qator(av, f, "1", bolim=a, mol=eski)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, b, rev, av=av)
    k = akt(rv, eski, yangi, t, rev)

    yakunla_va_yoz(rv, his)
    assert akt_qatorlari() == [(b.pk, ISH, D("1"))]
    akt_tasdiqla(k, his)

    t = Taqsimot.objects.get(av=av)
    assert (t.bolim, t.mol) == (b, yangi)


def test_holati_ozgargan_av_akti_tasdiqlanadi(f, his, rev, ab):
    a, _ = ab
    eski, yangi = xodim(), xodim()
    av = av_yarat(f)
    t = qator(av, f, "1", bolim=a, mol=eski)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, a, rev, av=av, holat=NOSOZ)
    k = akt(rv, eski, yangi, t, rev)

    yakunla_va_yoz(rv, his)
    akt_tasdiqla(k, his)

    assert Taqsimot.objects.get(av=av).mol == yangi


def test_qisman_kochganda_akt_qatori_bolinadi(f, his, rev, ab):
    a, b = ab
    eski, yangi = xodim(), xodim()
    av = av_yarat(f, soni="3")
    t = qator(av, f, "3", bolim=a, mol=eski)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, a, rev, av=av, soni=D("1"))
    qayd_qosh(rv, b, rev, av=av, soni=D("2"))
    k = akt(rv, eski, yangi, t, rev)

    yakunla_va_yoz(rv, his)

    assert akt_qatorlari() == sorted([(a.pk, ISH, D("1")), (b.pk, ISH, D("2"))])
    akt_tasdiqla(k, his)
    assert not Taqsimot.objects.filter(av=av).exclude(mol=yangi).exists()


def test_qaytarilganda_akt_qatori_ham_qaytadi(f, his, rev, ab):
    a, b = ab
    eski, yangi = xodim(), xodim()
    av = av_yarat(f)
    t = qator(av, f, "1", bolim=a, mol=eski)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, b, rev, av=av)
    akt(rv, eski, yangi, t, rev)

    yakunla_va_yoz(rv, his)
    ochiqqa_qaytar(rv, his)

    assert akt_qatorlari() == [(a.pk, ISH, D("1"))]


def test_boshqa_akt_va_boshqa_javobgar_qatoriga_tegmaydi(f, his, rev, ab):
    a, b = ab
    eski, yangi = xodim(), xodim()
    av = av_yarat(f)
    t = qator(av, f, "1", bolim=a, mol=eski)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, b, rev, av=av)
    qoralamaga_qosh(eski, yangi, [(t, t.soni)], rev, "reviziyaga aloqasi yo'q")

    yakunla_va_yoz(rv, his)

    assert akt_qatorlari() == [(a.pk, ISH, D("1"))]


def biriktir(rev, rv, av, xodim_, bolim):
    c = Client()
    c.force_login(rev)
    return c.post(reverse("reviziya:mobil_mol", args=[rv.pk]), {"av": av.pk, "xodim": xodim_.pk, "bolim": bolim.pk})


def test_biriktirish_faqat_shu_xonadagi_qatorni_oladi(f, his, rev, ab):
    a, b = ab
    m1, m2, yangi = xodim(), xodim(), xodim()
    av = av_yarat(f, soni="10")
    qator(av, f, "1", bolim=a, mol=m1)
    qator(av, f, "9", bolim=b, mol=m2)
    rv = reviziya_och(f, None, [rev], [], his)

    assert biriktir(rev, rv, av, yangi, a).status_code == 200

    assert akt_qatorlari() == [(a.pk, ISH, D("1"))]
    assert MolAkt.objects.get().topshiruvchi == m1


def test_xonada_qatori_yoq_bolsa_bir_dona_oladi(f, his, rev, ab):
    a, b = ab
    yangi = xodim()
    av = av_yarat(f, soni="5")
    qator(av, f, "5", bolim=a, mol=xodim())
    rv = reviziya_och(f, None, [rev], [], his)

    biriktir(rev, rv, av, yangi, b)

    assert akt_qatorlari() == [(a.pk, ISH, D("1"))]


def test_xonada_qatori_yoq_bolsa_topilgan_sonini_oladi(f, his, rev, ab):
    a, b = ab
    yangi = xodim()
    av = av_yarat(f, soni="5")
    qator(av, f, "5", bolim=a, mol=xodim())
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, b, rev, av=av, soni=D("3"))

    biriktir(rev, rv, av, yangi, b)

    assert akt_qatorlari() == [(a.pk, ISH, D("3"))]


def test_shu_xonadagi_av_allaqachon_shu_xodimda(f, his, rev, ab):
    a, b = ab
    yangi = xodim()
    av = av_yarat(f, soni="2")
    qator(av, f, "1", bolim=a, mol=yangi)
    qator(av, f, "1", bolim=b, mol=xodim())
    rv = reviziya_och(f, None, [rev], [], his)

    r = biriktir(rev, rv, av, yangi, a)

    assert r.status_code == 400 and not MolAktQator.objects.exists()
