from decimal import Decimal

import pytest

from reviziya.servis import qayd_qosh, reviziya_och
from reviziya.solishtir import GURUHLAR, jamlar, solishtir
from vositalar.models import Bolim, Holat
from vositalar.tests.test_bayroqlar import av_yarat, qator


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("07")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def revizor(foydalanuvchi):
    return foydalanuvchi("revizor")


@pytest.fixture
def och(hisobchi, revizor):
    def yarat(filial):
        return reviziya_och(filial, None, [revizor], [], hisobchi)

    return yarat


@pytest.fixture
def qosh(revizor):
    def yarat(rv, bolim, soni="1", **kw):
        return qayd_qosh(rv, bolim, revizor, soni=Decimal(soni), **kw)

    return yarat


def guruhlab(qatorlar):
    natija = {}
    for q in qatorlar:
        natija.setdefault(q.guruh, []).append(q)
    return natija


def test_hammasi_topildi(filial, och, qosh):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    stol = av_yarat(filial, inv="100")
    qator(stol, filial, "1", bolim=zal)
    rv = och(filial)
    qosh(rv, zal, av=stol)

    qatorlar = solishtir(rv)

    assert len(qatorlar) == 1
    q = qatorlar[0]
    assert (q.guruh, q.av_id, q.bolim_id, q.holat) == ("topildi", stol.pk, zal.pk, Holat.ISHLATILMOQDA)
    assert (q.kutilgan, q.topilgan, q.farq) == (Decimal("1"), Decimal("1"), Decimal("0"))
    assert (q.av_nomi, q.inv, q.bolim_nomi) == (stol.nomi, "100", "Zal")
    j = jamlar(qatorlar)
    assert j["topildi"] == 1
    assert set(j) == set(GURUHLAR) and all(j[g] == 0 for g in GURUHLAR if g != "topildi")


def test_topilmadi_va_kam(filial, och, qosh):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    stol = av_yarat(filial, soni="3")
    qator(stol, filial, "3", bolim=zal)
    rv = och(filial)

    qatorlar = solishtir(rv)
    assert [(q.guruh, q.kutilgan, q.topilgan, q.farq) for q in qatorlar] == [
        ("topilmadi", Decimal("3"), Decimal("0"), Decimal("-3"))
    ]
    assert jamlar(qatorlar)["topilmadi"] == 3

    qosh(rv, zal, av=stol)
    g = guruhlab(solishtir(rv))
    assert set(g) == {"kam", "topildi"}
    assert g["kam"][0].farq == Decimal("-2") and g["kam"][0].bolim_id == zal.pk
    assert g["topildi"][0].topilgan == Decimal("1")
    assert jamlar(solishtir(rv))["kam"] == 2


def test_boshqa_joyda_juftlik(filial, och, qosh):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "2", bolim=a)
    rv = och(filial)
    qosh(rv, b, soni="2", av=stol)

    qatorlar = solishtir(rv)

    assert len(qatorlar) == 1
    q = qatorlar[0]
    assert (q.guruh, q.bolim_id, q.nishon_bolim_id, q.holat, q.farq) == (
        "boshqa_joyda", a.pk, b.pk, Holat.ISHLATILMOQDA, Decimal("2")
    )
    assert jamlar(qatorlar)["boshqa_joyda"] == 2 and jamlar(qatorlar)["topilmadi"] == 0


def test_boshqa_joyda_qisman(filial, och, qosh):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="3")
    qator(stol, filial, "3", bolim=a)
    rv = och(filial)
    qosh(rv, b, soni="1", av=stol)

    g = guruhlab(solishtir(rv))

    assert set(g) == {"boshqa_joyda", "topilmadi"}
    assert (g["boshqa_joyda"][0].farq, g["boshqa_joyda"][0].nishon_bolim_id) == (Decimal("1"), b.pk)
    assert (g["topilmadi"][0].farq, g["topilmadi"][0].bolim_id) == (Decimal("-2"), a.pk)


def test_holat_boshqa(filial, och, qosh):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "2", bolim=zal)
    rv = och(filial)
    qosh(rv, zal, av=stol, holat=Holat.NOSOZ)
    qosh(rv, zal, av=stol, holat=Holat.ISHLATILMOQDA)

    g = guruhlab(solishtir(rv))

    assert set(g) == {"topildi", "holat_boshqa"}
    assert (g["topildi"][0].holat, g["topildi"][0].topilgan) == (Holat.ISHLATILMOQDA, Decimal("1"))
    hb = g["holat_boshqa"][0]
    assert (hb.holat, hb.nishon_holat, hb.farq, hb.bolim_id) == (Holat.ISHLATILMOQDA, Holat.NOSOZ, Decimal("1"), zal.pk)


def test_holat_boshqa_va_boshqa_joyda_aralash(filial, och, qosh):
    """Soni teng bo'lmagan bo'limda ham holat farqi avval o'z joyida juftlanadi, qolgani — boshqa joyda."""
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="3")
    qator(stol, filial, "3", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol, holat=Holat.NOSOZ)
    qosh(rv, b, av=stol, soni="2")

    g = guruhlab(solishtir(rv))

    assert set(g) == {"holat_boshqa", "boshqa_joyda"}
    assert g["holat_boshqa"][0].farq == Decimal("1")
    assert (g["boshqa_joyda"][0].farq, g["boshqa_joyda"][0].nishon_bolim_id) == (Decimal("2"), b.pk)


def test_ortiqcha_va_nomalum(filial, och, qosh):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    rv = och(filial)
    stol = av_yarat(filial, inv="5")
    qator(stol, filial, "1", bolim=zal)  # surat olingandan keyin — kutilmaydi
    qosh(rv, zal, av=stol)
    qosh(rv, zal, qr_matn="XYZ-1")
    qosh(rv, None, qr_matn="XYZ-1", soni="2")

    qatorlar = solishtir(rv)

    assert {q.guruh for q in qatorlar} == {"ortiqcha"}
    av_qator = next(q for q in qatorlar if q.av_id == stol.pk)
    assert (av_qator.topilgan, av_qator.farq, av_qator.kutilgan) == (Decimal("1"), Decimal("1"), Decimal("0"))
    qr = sorted((q for q in qatorlar if q.av_id is None), key=lambda q: q.bolim_nomi)
    assert [(q.qr_matn, q.bolim_id, q.topilgan, q.av_nomi, q.inv) for q in qr] == [
        ("XYZ-1", None, Decimal("2"), "", ""),
        ("XYZ-1", zal.pk, Decimal("1"), "", ""),
    ]
    assert qr[0].bolim_nomi == "Bo'limsiz"
    assert qr[1].kalit == f"ortiqcha:qr:XYZ-1:{zal.pk}"
    assert jamlar(qatorlar)["ortiqcha"] == 4


def test_kalit_barqaror(filial, och, qosh):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="4")
    qator(stol, filial, "4", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol, holat=Holat.NOSOZ)
    qosh(rv, b, av=stol)
    qosh(rv, b, qr_matn="??")

    birinchi = [q.kalit for q in solishtir(rv)]
    ikkinchi = [q.kalit for q in solishtir(rv)]

    assert birinchi == ikkinchi
    assert len(set(birinchi)) == len(birinchi)
    assert f"boshqa_joyda:{stol.pk}:{a.pk}:{Holat.ISHLATILMOQDA}:{b.pk}:" in birinchi


def test_arxiv_av_ortiqcha(filial, och, qosh):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    arxiv = av_yarat(filial, soni="0")
    qator(arxiv, filial, "1", bolim=zal)
    rv = och(filial)
    qosh(rv, zal, av=arxiv)

    qatorlar = solishtir(rv)

    assert [(q.guruh, q.av_id, q.topilgan) for q in qatorlar] == [("ortiqcha", arxiv.pk, Decimal("1"))]


def test_mol_boyicha_qatorlar_yigiladi_va_tartib(filial, och, qosh):
    from vositalar.tests.test_bayroqlar import xodim

    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "1", bolim=a, mol=xodim())
    qator(stol, filial, "1", bolim=a, mol=xodim())
    stul = av_yarat(filial)
    qator(stul, filial, "1", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol, soni="2")

    qatorlar = solishtir(rv)

    assert [(q.guruh, q.av_id, q.kutilgan) for q in qatorlar] == [
        ("topilmadi", stul.pk, Decimal("1")),
        ("topildi", stol.pk, Decimal("2")),
    ]


def test_boshqa_joyda_boshqa_holat(filial, och, qosh):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "2", bolim=a)
    rv = och(filial)
    qosh(rv, b, soni="2", av=stol, holat=Holat.NOSOZ)

    qatorlar = solishtir(rv)

    assert len(qatorlar) == 1
    q = qatorlar[0]
    assert (q.guruh, q.bolim_id, q.holat, q.nishon_bolim_id, q.nishon_holat, q.farq) == (
        "boshqa_joyda", a.pk, Holat.ISHLATILMOQDA, b.pk, Holat.NOSOZ, Decimal("2")
    )
    assert q.kalit.endswith(f":{b.pk}:nosoz")


def test_boshqa_joyda_aralash_holat(filial, och, qosh):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "2", bolim=a)
    rv = och(filial)
    qosh(rv, b, av=stol, holat=Holat.NOSOZ)
    qosh(rv, b, av=stol, holat=Holat.ISHLATILMOQDA)

    qatorlar = solishtir(rv)

    assert {q.guruh for q in qatorlar} == {"boshqa_joyda"}
    assert sorted((q.nishon_holat, q.farq) for q in qatorlar) == [("", Decimal("1")), (Holat.NOSOZ, Decimal("1"))]
    assert len({q.kalit for q in qatorlar}) == 2
