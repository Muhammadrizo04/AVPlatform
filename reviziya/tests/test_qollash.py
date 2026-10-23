from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from reviziya.models import Reviziya, ReviziyaQollash
from reviziya.qollash import qolla, reviziya_yop
from reviziya.servis import ReviziyaXato, qayd_qosh, reviziya_och, yakunla
from reviziya.solishtir import solishtir
from vositalar.amallar import kochir, mol_ozgartir
from vositalar.models import Bolim, Holat, Taqsimot, TaqsimotHarakat
from vositalar.tests.test_bayroqlar import av_yarat, qator, xodim


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


def kalit(rv, guruh, av):
    return next(q.kalit for q in solishtir(rv) if q.guruh == guruh and q.av_id == av.pk)


def taqsimot(av):
    return sorted((t.bolim_id, t.holat, t.soni) for t in Taqsimot.objects.filter(av=av))


def test_boshqa_joyda_kochiradi(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="3")
    qator(stol, filial, "3", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol)
    qosh(rv, b, "2", av=stol)
    yakunla(rv, hisobchi)

    [natija] = qolla(rv, [kalit(rv, "boshqa_joyda", stol)], hisobchi)

    assert (natija.natija, natija.guruh, natija.soni, natija.xato) == ("ok", "boshqa_joyda", Decimal("2"), "")
    assert taqsimot(stol) == [(a.pk, Holat.ISHLATILMOQDA, Decimal("1")), (b.pk, Holat.ISHLATILMOQDA, Decimal("2"))]
    h = TaqsimotHarakat.objects.get(av=stol)
    assert (h.sabab, h.hujjat_izoh, h.soni) == ("reviziya", rv.nomi, Decimal("2"))


def test_boshqa_joyda_holat_ham_ozgaradi(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial, soni="1")
    qator(stol, filial, "1", bolim=a)
    rv = och(filial)
    qosh(rv, b, av=stol, holat=Holat.NOSOZ)
    yakunla(rv, hisobchi)

    [natija] = qolla(rv, [kalit(rv, "boshqa_joyda", stol)], hisobchi)

    assert natija.natija == "ok"
    assert taqsimot(stol) == [(b.pk, Holat.NOSOZ, Decimal("1"))]
    assert set(TaqsimotHarakat.objects.filter(av=stol).values_list("sabab", "hujjat_izoh")) == {
        ("reviziya", rv.nomi)
    }


def test_topilmadi_holat(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "2", bolim=a)
    rv = och(filial)
    yakunla(rv, hisobchi)

    [natija] = qolla(rv, [kalit(rv, "topilmadi", stol)], hisobchi)

    assert (natija.natija, natija.soni) == ("ok", Decimal("2"))
    assert taqsimot(stol) == [(a.pk, Holat.TOPILMADI, Decimal("2"))]
    assert TaqsimotHarakat.objects.get(av=stol).sabab == "reviziya"


def test_kam_qismi_topilmadi(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial, soni="3")
    qator(stol, filial, "3", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol)
    yakunla(rv, hisobchi)

    [natija] = qolla(rv, [kalit(rv, "kam", stol)], hisobchi)

    assert (natija.natija, natija.soni) == ("ok", Decimal("2"))
    assert taqsimot(stol) == [(a.pk, Holat.ISHLATILMOQDA, Decimal("1")), (a.pk, Holat.TOPILMADI, Decimal("2"))]


def test_holat_boshqa_qollash(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial, soni="2")
    qator(stol, filial, "2", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol)
    qosh(rv, a, av=stol, holat=Holat.TAMIRDA)
    yakunla(rv, hisobchi)

    [natija] = qolla(rv, [kalit(rv, "holat_boshqa", stol)], hisobchi)

    assert (natija.natija, natija.soni) == ("ok", Decimal("1"))
    assert taqsimot(stol) == [(a.pk, Holat.ISHLATILMOQDA, Decimal("1")), (a.pk, Holat.TAMIRDA, Decimal("1"))]


def test_bir_nechta_mol_qatoridan_yigiladi(filial, och, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial, soni="3")
    t = qator(stol, filial, "3", bolim=a)
    rv = och(filial)
    yakunla(rv, hisobchi)
    mol_ozgartir(t, Decimal("1"), xodim(), hisobchi)  # snapshotdan keyin: 2 + 1 (boshqa МОЛ)

    [natija] = qolla(rv, [kalit(rv, "topilmadi", stol)], hisobchi)

    assert natija.natija == "ok"
    assert taqsimot(stol) == [(a.pk, Holat.TOPILMADI, Decimal("1")), (a.pk, Holat.TOPILMADI, Decimal("2"))]


def test_taqsimot_ozgargan(filial, och, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    c = Bolim.objects.create(filial=filial, nomi="C")
    stol = av_yarat(filial, soni="2")
    stul = av_yarat(filial, soni="1")
    t = qator(stol, filial, "2", bolim=a)
    qator(stul, filial, "1", bolim=a)
    rv = och(filial)
    yakunla(rv, hisobchi)
    kochir(t, Decimal("1"), c, hisobchi)  # snapshotdan keyin A'da faqat 1 qoldi
    harakatlar = TaqsimotHarakat.objects.count()

    stol_n, stul_n = qolla(rv, [kalit(rv, "topilmadi", stol), kalit(rv, "topilmadi", stul)], hisobchi)

    assert stol_n.natija == "xato" and stol_n.xato.startswith("Taqsimot o'zgargan:")
    assert stol.nomi in stol_n.xato
    assert stul_n.natija == "ok"
    # stol qisman ham qo'llanmagan
    assert taqsimot(stol) == [(a.pk, Holat.ISHLATILMOQDA, Decimal("1")), (c.pk, Holat.ISHLATILMOQDA, Decimal("1"))]
    assert TaqsimotHarakat.objects.count() == harakatlar + 1


def test_nofaol_bolim(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    stol = av_yarat(filial)
    qator(stol, filial, "1", bolim=a)
    rv = och(filial)
    qosh(rv, b, av=stol)
    yakunla(rv, hisobchi)
    Bolim.objects.filter(pk=b.pk).update(faol=False)

    [natija] = qolla(rv, [kalit(rv, "boshqa_joyda", stol)], hisobchi)

    assert (natija.natija, natija.xato) == ("xato", "Bo'lim faol emas.")
    assert taqsimot(stol) == [(a.pk, Holat.ISHLATILMOQDA, Decimal("1"))]


def test_qayta_qollash_yoq(filial, och, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial)
    qator(stol, filial, "1", bolim=a)
    rv = och(filial)
    yakunla(rv, hisobchi)
    k = kalit(rv, "topilmadi", stol)

    [birinchi] = qolla(rv, [k], hisobchi)
    [ikkinchi] = qolla(rv, [k], hisobchi)

    assert birinchi.natija == "ok"
    assert ikkinchi.natija == "xato" and "allaqachon qo'llangan" in ikkinchi.xato
    assert TaqsimotHarakat.objects.filter(av=stol).count() == 1


def test_qollab_bolmaydigan_va_nomalum_kalit(filial, och, qosh, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial)
    qator(stol, filial, "1", bolim=a)
    rv = och(filial)
    qosh(rv, a, av=stol)
    qosh(rv, a, qr_matn="XYZ")
    yakunla(rv, hisobchi)
    qr_kalit = next(q.kalit for q in solishtir(rv) if q.av_id is None)

    natijalar = qolla(rv, [kalit(rv, "topildi", stol), qr_kalit, "topilmadi:0:None:x:None:"], hisobchi)

    assert [(n.natija, n.xato) for n in natijalar] == [
        ("xato", "Bu qatorni qo'llab bo'lmaydi."),
        ("xato", "Bu qatorni qo'llab bo'lmaydi."),
        ("xato", "Qator topilmadi."),
    ]
    assert ReviziyaQollash.objects.filter(reviziya=rv).count() == 3


def test_faqat_yakunlangan(filial, och, hisobchi):
    rv = och(filial)
    with pytest.raises(ReviziyaXato):
        qolla(rv, [], hisobchi)
    with pytest.raises(ReviziyaXato):
        reviziya_yop(rv, hisobchi)


def test_reviziya_yop(filial, och, hisobchi):
    rv = och(filial)
    yakunla(rv, hisobchi)

    reviziya_yop(rv, hisobchi)

    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.QOLLANGAN
    assert rv.qolladi == hisobchi and rv.qollangan_vaqt is not None
    with pytest.raises(ReviziyaXato):
        qolla(rv, [], hisobchi)


def test_ok_qollash_noyob(filial, och, hisobchi):
    rv = och(filial)
    kw = dict(reviziya=rv, kalit="k", guruh="kam", soni=1, kim=hisobchi)
    ReviziyaQollash.objects.create(natija="xato", xato="a", **kw)
    ReviziyaQollash.objects.create(natija="xato", xato="b", **kw)
    ReviziyaQollash.objects.create(natija="ok", **kw)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviziyaQollash.objects.create(natija="ok", **kw)


def test_topilmadi_holatidagi_qator_ozgarmaydi(filial, och, hisobchi):
    a = Bolim.objects.create(filial=filial, nomi="A")
    stol = av_yarat(filial)
    Taqsimot.objects.create(av=stol, filial=filial, bolim=a, holat=Holat.TOPILMADI, soni=Decimal("1"))
    rv = och(filial)
    yakunla(rv, hisobchi)

    [natija] = qolla(rv, [kalit(rv, "topilmadi", stol)], hisobchi)

    assert natija.natija == "ok"
    assert taqsimot(stol) == [(a.pk, Holat.TOPILMADI, Decimal("1"))]
    assert not TaqsimotHarakat.objects.filter(av=stol).exists()
