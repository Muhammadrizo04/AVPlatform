"""Reviziya mantig'i: eskirgan surat, «Hammasi joyida», ko'chgan AV yorlig'i, chala yakunlash, ochiqqa qaytarish."""
from decimal import Decimal as D

import pytest
from django.test import Client
from django.urls import reverse

from reviziya.models import Reviziya
from reviziya.qollash import ochiqqa_qaytar, yakunla_va_yoz
from reviziya.servis import (
    BOSHQA_FILIAL, ReviziyaXato, qayd_qosh, qr_tahlil, reviziya_och, sanalmagan_xonalar, xona_tugadi,
)
from vositalar.amallar import holat_ozgartir, kochir, mol_ozgartir
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


def holatli(av, filial, soni, bolim, holat, mol=None):
    return Taqsimot.objects.create(av=av, filial=filial, bolim=bolim, mol=mol, holat=holat, soni=D(soni))


def tq(av):
    return sorted((t.bolim_id or 0, t.holat, t.soni) for t in Taqsimot.objects.filter(av=av))


def kirgan(u):
    c = Client()
    c.force_login(u)
    return c


def bolimlar(f, *nomlar):
    return [Bolim.objects.create(filial=f, nomi=n) for n in nomlar]


# --- 1. Reviziya ochiq paytdagi o'zgarishlar


def test_ochiq_paytda_kochirilgan_av_ga_kamomad_yozilmaydi(f, his, rev):
    a, b = bolimlar(f, "A", "B")
    av = av_yarat(f, soni="5")
    t = qator(av, f, "5", bolim=a)
    rv = reviziya_och(f, a, [rev], [], his)
    kochir(t, D("2"), b, his)
    qayd_qosh(rv, a, rev, av=av, soni=D("3"))

    [n] = yakunla_va_yoz(rv, his)

    assert n.natija == "xato" and "Reviziya ochilgandan keyin" in n.xato
    assert tq(av) == sorted([(a.pk, ISH, D("3")), (b.pk, ISH, D("2"))])


def test_ochiq_paytda_holat_ozgargan_av_ham_yozilmaydi(f, his, rev):
    a, = bolimlar(f, "A")
    av = av_yarat(f, soni="2")
    t = qator(av, f, "2", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    holat_ozgartir(t, D("1"), NOSOZ, his)

    [n] = yakunla_va_yoz(rv, his)

    assert n.natija == "xato"
    assert tq(av) == sorted([(a.pk, ISH, D("1")), (a.pk, NOSOZ, D("1"))])


def test_ochiq_paytdagi_mol_akti_yozishni_toxtatmaydi(f, his, rev):
    """МОЛ o'zgarishi bo'lim, holat va sonni o'zgartirmaydi — surat eskirmaydi."""
    a, b = bolimlar(f, "A", "B")
    av = av_yarat(f, soni="1")
    t = qator(av, f, "1", bolim=a, mol=xodim())
    rv = reviziya_och(f, None, [rev], [], his)
    mol_ozgartir(t, D("1"), xodim(), his)
    qayd_qosh(rv, b, rev, av=av)

    [n] = yakunla_va_yoz(rv, his)

    assert n.natija == "ok" and tq(av) == [(b.pk, ISH, D("1"))]


def test_qayta_yakunlashda_oz_harakatlari_toxtatmaydi(f, his, rev):
    a, b = bolimlar(f, "A", "B")
    av = av_yarat(f, soni="1")
    qator(av, f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, b, rev, av=av)
    yakunla_va_yoz(rv, his)
    ochiqqa_qaytar(rv, his)

    [n] = yakunla_va_yoz(rv, his)

    assert n.natija == "ok" and tq(av) == [(b.pk, ISH, D("1"))]


# --- 2. «Hammasi joyida»


def hammasi_bor(rev, rv, bolim):
    return kirgan(rev).post(reverse("reviziya:mobil_hammasi_bor", args=[rv.pk]), {"bolim": bolim.pk})


def test_hammasi_joyida_har_holatni_saqlaydi(f, his, rev):
    a, = bolimlar(f, "A")
    av = av_yarat(f, soni="5")
    holatli(av, f, "3", a, ISH)
    holatli(av, f, "2", a, NOSOZ)
    rv = reviziya_och(f, None, [rev], [], his)

    assert hammasi_bor(rev, rv, a).status_code == 200

    assert sorted(rv.qaydlar.values_list("holat", "soni")) == sorted([(ISH, D("3")), (NOSOZ, D("2"))])
    assert yakunla_va_yoz(rv, his) == []


def test_hammasi_joyida_qisman_sanalgandan_keyin_faqat_qolganini_oladi(f, his, rev):
    a, = bolimlar(f, "A")
    av = av_yarat(f, soni="5")
    holatli(av, f, "3", a, ISH)
    holatli(av, f, "2", a, NOSOZ)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, a, rev, av=av, soni=D("1"), holat=NOSOZ)

    hammasi_bor(rev, rv, a)

    assert sorted(rv.qaydlar.values_list("holat", "soni")) == sorted([(ISH, D("3")), (NOSOZ, D("2"))])


def test_hammasi_joyida_topilmaganni_belgilamaydi(f, his, rev):
    a, = bolimlar(f, "A")
    yoqolgan, stol = av_yarat(f, inv="Y", soni="1"), av_yarat(f, inv="S", soni="1")
    holatli(yoqolgan, f, "1", a, TOP)
    qator(stol, f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)

    r = hammasi_bor(rev, rv, a)

    assert "1 ta AV belgilandi" in r.content.decode()
    assert list(rv.qaydlar.values_list("av_id", flat=True)) == [stol.pk]


# --- 3. Filiali o'zgargan AV yorlig'i


def test_kochib_kelgan_av_yorligi_taniladi(filial_yarat, his, rev):
    x, y = filial_yarat("01"), filial_yarat("02")
    a, = bolimlar(y, "A")
    av = av_yarat(x, inv="INV9", soni="1", qoldiq_filial=y)
    qator(av, y, "1", bolim=a)
    rv = reviziya_och(y, None, [rev], [], his)

    assert qr_tahlil("DS|01|INV9", rv) == (av, "")

    qayd_qosh(rv, a, rev, av=av)
    assert yakunla_va_yoz(rv, his) == []
    assert tq(av) == [(a.pk, ISH, D("1"))]


def test_haqiqatan_boshqa_filial_yorligi_ozgarmaydi(filial_yarat, his, rev):
    x, y = filial_yarat("01"), filial_yarat("02")
    av_yarat(x, inv="INV9", soni="1")
    rv = reviziya_och(y, None, [rev], [], his)

    assert qr_tahlil("DS|01|INV9", rv) == (None, BOSHQA_FILIAL)


# --- 4. Chala yakunlash


def test_sanalmagan_xona_bilan_yakunlab_bolmaydi(f, his, rev):
    a, b = bolimlar(f, "A", "B")
    stol, kreslo = av_yarat(f, inv="S", soni="1"), av_yarat(f, inv="K", soni="1")
    qator(stol, f, "1", bolim=a)
    qator(kreslo, f, "1", bolim=b)
    rv = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv, a, rev, av=stol)

    r = kirgan(his).post(reverse("reviziya:yakunla", args=[rv.pk]), follow=True)

    assert "Sanalmagan xonalar" in r.content.decode()
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.OCHIQ
    assert tq(kreslo) == [(b.pk, ISH, D("1"))]


def test_xona_tugadi_belgisi_yakunlashga_ruxsat_beradi(f, his, rev):
    """Xona sanaldi, hech narsa topilmadi — bu haqiqiy kamomad, «Xona tugadi» shuni tasdiqlaydi."""
    a, = bolimlar(f, "A")
    av = av_yarat(f, soni="1")
    qator(av, f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)
    assert [x["nomi"] for x in sanalmagan_xonalar(rv)] == ["A"]
    xona_tugadi(rv, a, rev)
    assert sanalmagan_xonalar(rv) == []

    kirgan(his).post(reverse("reviziya:yakunla", args=[rv.pk]))

    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN
    assert tq(av) == [(a.pk, TOP, D("1"))]


def test_sahifada_sanalmagan_xonalar_oldindan_korinadi(f, his, rev):
    a, = bolimlar(f, "A")
    qator(av_yarat(f, soni="1"), f, "1", bolim=a)
    rv = reviziya_och(f, None, [rev], [], his)

    assert "Sanalmagan xonalar" in kirgan(his).get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()


# --- 5. Ochiqqa qaytarish


def test_kesishgan_ochiq_reviziya_bolsa_qaytarilmaydi(f, his, rev):
    a, = bolimlar(f, "A")
    av = av_yarat(f, soni="1")
    qator(av, f, "1", bolim=a)
    rv1 = reviziya_och(f, None, [rev], [], his)
    yakunla_va_yoz(rv1, his)
    reviziya_och(f, a, [rev], [], his)

    with pytest.raises(ReviziyaXato, match="ochiq reviziya"):
        ochiqqa_qaytar(rv1, his)

    rv1.refresh_from_db()
    assert rv1.holat == Reviziya.Holat.YAKUNLANGAN
    assert tq(av) == [(a.pk, TOP, D("1"))]


def test_keyingi_yakunlangan_reviziya_bolsa_qaytarilmaydi(f, his, rev):
    a, b = bolimlar(f, "A", "B")
    av = av_yarat(f, soni="1")
    qator(av, f, "1", bolim=a)
    rv1 = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv1, b, rev, av=av)
    yakunla_va_yoz(rv1, his)
    rv2 = reviziya_och(f, None, [rev], [], his)
    qayd_qosh(rv2, b, rev, av=av)
    yakunla_va_yoz(rv2, his)

    with pytest.raises(ReviziyaXato, match=rv2.nomi):
        ochiqqa_qaytar(rv1, his)

    assert tq(av) == [(b.pk, ISH, D("1"))]


def test_kesishmagan_reviziya_qaytarishga_xalaqit_bermaydi(f, his, rev):
    a, b = bolimlar(f, "A", "B")
    av = av_yarat(f, soni="1")
    qator(av, f, "1", bolim=a)
    rv1 = reviziya_och(f, a, [rev], [], his)
    yakunla_va_yoz(rv1, his)
    reviziya_och(f, b, [rev], [], his)

    ochiqqa_qaytar(rv1, his)

    rv1.refresh_from_db()
    assert rv1.holat == Reviziya.Holat.OCHIQ
