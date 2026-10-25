import uuid
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import pytest

from jurnal.models import Jurnal
from onec.models import AV, AVQoldiq, Harakat1C, Xodim
from vositalar.amallar import AmalXato, holat_ozgartir, kamaytir, kochir, mol_ozgartir
from vositalar.models import Bolim, Holat, Taqsimot, TaqsimotHarakat
from vositalar.moslash import farq

SON = Decimal
Sabab = TaqsimotHarakat.Sabab


@pytest.fixture
def av(db):
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def user(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def ombor(filial):
    return Bolim.objects.create(filial=filial, nomi="Ombor")


@pytest.fixture
def ofis(filial):
    return Bolim.objects.create(filial=filial, nomi="Ofis")


def qoldiq(av, filial, soni):
    return AVQoldiq.objects.create(av=av, filial=filial, soni=SON(soni), summa=SON("100"))


def qator(av, filial, soni, bolim=None, mol=None, holat=Holat.ISHLATILMOQDA):
    return Taqsimot.objects.create(av=av, filial=filial, bolim=bolim, mol=mol, holat=holat, soni=SON(soni))


def jami(av, filial):
    return sum(t.soni for t in Taqsimot.objects.filter(av=av, filial=filial))


def test_kochir_qisman_bolinadi(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)

    yangi = kochir(q, SON("4"), ofis, user)

    q.refresh_from_db()
    assert (q.bolim, q.soni) == (ombor, SON("2"))
    assert (yangi.bolim, yangi.soni, yangi.holat) == (ofis, SON("4"), Holat.ISHLATILMOQDA)
    assert Taqsimot.objects.count() == 2
    assert farq(av, filial) == 0


def test_kochir_birlashadi(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "9")
    q = qator(av, filial, "6", bolim=ombor)
    mavjud = qator(av, filial, "3", bolim=ofis)

    natija = kochir(q, SON("4"), ofis, user)

    assert natija.pk == mavjud.pk
    mavjud.refresh_from_db()
    assert mavjud.soni == SON("7")
    assert Taqsimot.objects.count() == 2
    assert Taqsimot.objects.get(bolim=ombor).soni == SON("2")
    assert farq(av, filial) == 0


def test_mol_olib_tashlash_bosh_molli_qatorga_birlashadi(av, filial, ombor, user):
    """Bo'sh МОЛ (NULL) ham bir xil qiymat: yangi qator ochilmaydi, mavjudiga qo'shiladi."""
    qoldiq(av, filial, "5")
    mol = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Ali", filial=filial)
    q = qator(av, filial, "2", bolim=ombor, mol=mol)
    mavjud = qator(av, filial, "3", bolim=ombor)

    natija = mol_ozgartir(q, SON("2"), None, user)

    assert natija.pk == mavjud.pk and natija.soni == SON("5")
    assert Taqsimot.objects.count() == 1


def test_kochir_toliq_qator_ochadi(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)

    yangi = kochir(q, SON("6"), ofis, user)

    assert not Taqsimot.objects.filter(pk=q.pk).exists()
    assert Taqsimot.objects.get() == yangi
    assert (yangi.bolim, yangi.soni) == (ofis, SON("6"))
    assert farq(av, filial) == 0


def test_boshqa_filial_bolimi_rad(av, filial, filial_yarat, ombor, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)
    boshqa = Bolim.objects.create(filial=filial_yarat("B"), nomi="Boshqa")

    with pytest.raises(AmalXato, match="boshqa filial"):
        kochir(q, SON("1"), boshqa, user)

    q.refresh_from_db()
    assert q.soni == SON("6")
    assert not TaqsimotHarakat.objects.exists()


def test_nofaol_bolim_rad(av, filial, ombor, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6")
    nofaol = Bolim.objects.create(filial=filial, nomi="Yopilgan", faol=False)

    with pytest.raises(AmalXato, match="faol emas"):
        kochir(q, SON("1"), nofaol, user)


def test_bir_xil_bolimga_kochirish_rad(av, filial, ombor, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)

    with pytest.raises(AmalXato):
        kochir(q, SON("1"), ombor, user)

    assert Taqsimot.objects.get().soni == SON("6")


@pytest.mark.parametrize("soni", ["0", "-1", "7", "1.0005", "NaN"])
def test_soni_chegara(av, filial, ombor, ofis, user, soni):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)

    with pytest.raises(AmalXato):
        kochir(q, SON(soni), ofis, user)

    assert Taqsimot.objects.get().soni == SON("6")
    assert not TaqsimotHarakat.objects.exists()


def test_soni_qator_soniga_teng_yoki_kasrli_ruxsat(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "6.5")
    q = qator(av, filial, "6.5", bolim=ombor)

    kochir(q, SON("0.5"), ofis, user)

    assert Taqsimot.objects.get(bolim=ombor).soni == SON("6")


def test_eskirgan_qator_soni_qulflangan_qatordan_tekshiriladi(av, filial, ombor, ofis, user):
    """Foydalanuvchi ko'rgan (eskirgan) obyektda soni 6, bazada esa boshqasi allaqachon ko'chirgan (2 qolgan)."""
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)
    eskirgan = Taqsimot.objects.get(pk=q.pk)
    kochir(q, SON("4"), ofis, user)

    with pytest.raises(AmalXato, match="oshib ketdi"):
        kochir(eskirgan, SON("5"), ofis, user)

    assert Taqsimot.objects.get(bolim=ombor).soni == SON("2")
    assert Taqsimot.objects.get(bolim=ofis).soni == SON("4")


def test_ochirilgan_qator_rad(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)
    eskirgan = Taqsimot.objects.get(pk=q.pk)
    kochir(q, SON("6"), ofis, user)

    with pytest.raises(AmalXato, match="topilmadi"):
        kochir(eskirgan, SON("1"), ofis, user)


def test_holat_ozgartir_2_tasi_nosoz(av, filial, ombor, user):
    qoldiq(av, filial, "5")
    q = qator(av, filial, "5", bolim=ombor)

    yangi = holat_ozgartir(q, SON("2"), Holat.NOSOZ, user)

    q.refresh_from_db()
    assert (q.holat, q.soni) == (Holat.ISHLATILMOQDA, SON("3"))
    assert (yangi.holat, yangi.soni, yangi.bolim) == (Holat.NOSOZ, SON("2"), ombor)
    assert farq(av, filial) == 0
    h = TaqsimotHarakat.objects.get()
    assert (h.eski_holat, h.yangi_holat, h.sabab) == (Holat.ISHLATILMOQDA, Holat.NOSOZ, Sabab.HOLAT)


def test_holat_bir_xil_yoki_notogri_rad(av, filial, ombor, user):
    qoldiq(av, filial, "5")
    q = qator(av, filial, "5", bolim=ombor)

    with pytest.raises(AmalXato):
        holat_ozgartir(q, SON("1"), Holat.ISHLATILMOQDA, user)
    with pytest.raises(AmalXato):
        holat_ozgartir(q, SON("1"), "yoq_holat", user)


def test_mol_ozgartir(av, filial, ombor, user):
    qoldiq(av, filial, "5")
    mol = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Ali", filial=filial)
    q = qator(av, filial, "5", bolim=ombor)

    yangi = mol_ozgartir(q, SON("5"), mol, user, hujjat_izoh="Akt 7")

    assert not Taqsimot.objects.filter(pk=q.pk).exists()
    assert (yangi.mol, yangi.soni, yangi.bolim) == (mol, SON("5"), ombor)
    h = TaqsimotHarakat.objects.get()
    assert (h.sabab, h.hujjat_izoh, h.yangi_mol, h.eski_mol) == (Sabab.MOL_AKT, "Akt 7", mol, None)

    # МОЛ'ni olib tashlash: bir xil mol -> no-op, boshqasi None -> yangi qator
    with pytest.raises(AmalXato):
        mol_ozgartir(yangi, SON("1"), mol, user)
    qaytgan = mol_ozgartir(yangi, SON("2"), None, user)
    assert (qaytgan.mol, qaytgan.soni) == (None, SON("2"))


def test_kamaytir_faqat_mos_emas_bolsa(av, filial, ombor, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)
    assert farq(av, filial) == 0
    with pytest.raises(AmalXato):
        kamaytir(q, SON("1"), user)

    AVQoldiq.objects.filter(av=av, filial=filial).update(soni=SON("1"))  # farq == -5
    assert farq(av, filial) == -5

    with pytest.raises(AmalXato):
        kamaytir(q, SON("6"), user)
    q.refresh_from_db()
    assert q.soni == SON("6")

    kamaytir(q, SON("5"), user)

    q.refresh_from_db()
    assert q.soni == SON("1")
    assert farq(av, filial) == 0
    h = TaqsimotHarakat.objects.get()
    assert h.sabab == Sabab.ONEC_KAMAYDI and h.soni == SON("5")
    assert (h.eski_bolim, h.eski_holat) == (ombor, Holat.ISHLATILMOQDA)
    assert (h.yangi_bolim, h.yangi_mol, h.yangi_holat) == (None, None, "")


def test_kamaytir_toliq_qator_ochadi_va_hujjat_izohi(av, filial, ombor, user):
    qoldiq(av, filial, "2")
    taqsim = qator(av, filial, "2")
    ombor_q = qator(av, filial, "3", bolim=ombor)
    for raqam, kun in (("11", 1), ("12", 5)):
        Harakat1C.objects.create(
            sana=datetime(2026, 10, kun, tzinfo=dt_timezone.utc), hujjat_turi="Hisobdan chiqarish",
            hujjat_raqami=raqam, hujjat_ref=uuid.uuid4(), av=av, filial=filial,
            vid=Harakat1C.Vid.CHIQIM, soni=SON("1"), summa=SON("1"),
        )
    assert farq(av, filial) == -3

    kamaytir(ombor_q, SON("3"), user)

    assert not Taqsimot.objects.filter(pk=ombor_q.pk).exists()
    assert Taqsimot.objects.get() == taqsim
    assert farq(av, filial) == 0
    assert TaqsimotHarakat.objects.get().hujjat_izoh == "Hisobdan chiqarish 12"


def test_kamaytir_1c_harakatisiz_izoh_bosh(av, filial, user):
    qoldiq(av, filial, "1")
    q = qator(av, filial, "2")

    kamaytir(q, SON("1"), user)

    assert TaqsimotHarakat.objects.get().hujjat_izoh == ""


def test_arxiv_av_rad(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "0")
    q = qator(av, filial, "3", bolim=ombor)

    with pytest.raises(AmalXato, match="Arxiv"):
        kochir(q, SON("1"), ofis, user)
    with pytest.raises(AmalXato, match="Arxiv"):
        holat_ozgartir(q, SON("1"), Holat.NOSOZ, user)
    with pytest.raises(AmalXato, match="Arxiv"):
        mol_ozgartir(q, SON("1"), None, user)
    with pytest.raises(AmalXato, match="Arxiv"):
        kamaytir(q, SON("1"), user)

    assert Taqsimot.objects.get().soni == SON("3")
    assert not TaqsimotHarakat.objects.exists()


def test_arxiv_hisobi_barcha_filiallar_boyicha(av, filial, filial_yarat, ombor, ofis, user):
    """Shu filialda 0, lekin boshqasida > 0 bo'lsa AV arxivda emas."""
    qoldiq(av, filial, "0")
    qoldiq(av, filial_yarat("B"), "4")
    q = qator(av, filial, "3", bolim=ombor)

    kochir(q, SON("1"), ofis, user)

    assert Taqsimot.objects.get(bolim=ofis).soni == SON("1")


def test_harakat_va_jurnal_yoziladi(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "9")
    q = qator(av, filial, "6", bolim=ombor)
    mavjud = qator(av, filial, "3", bolim=ofis)

    kochir(q, SON("4"), ofis, user)

    h = TaqsimotHarakat.objects.get()
    assert h.kim == user and h.sabab == Sabab.KOCHIRISH and h.soni == SON("4")
    assert (h.av, h.filial) == (av, filial)
    assert (h.eski_bolim, h.yangi_bolim) == (ombor, ofis)
    assert (h.eski_holat, h.yangi_holat) == (Holat.ISHLATILMOQDA, Holat.ISHLATILMOQDA)

    jurnal = {
        j.obyekt_id: (SON(j.eski), SON(j.yangi))
        for j in Jurnal.objects.filter(obyekt_turi="vositalar.taqsimot", maydon="soni")
    }
    assert jurnal == {str(q.pk): (SON("6"), SON("2")), str(mavjud.pk): (SON("3"), SON("7"))}
    assert all(j.kim == user for j in Jurnal.objects.all())


def test_jurnal_toliq_ochirilgan_qator_uchun(av, filial, ombor, ofis, user):
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)

    yangi = kochir(q, SON("6"), ofis, user)

    j = {x.obyekt_id: (SON(x.eski), SON(x.yangi)) for x in Jurnal.objects.all()}
    assert j == {str(q.pk): (SON("6"), SON("0")), str(yangi.pk): (SON("0"), SON("6"))}


def test_xato_tranzaksiyani_orqaga_qaytaradi(av, filial, ombor, ofis, user, monkeypatch):
    """Amal o'rtasida xato bo'lsa hech narsa saqlanmaydi."""
    qoldiq(av, filial, "6")
    q = qator(av, filial, "6", bolim=ombor)

    def buzuq(*args, **kwargs):
        raise RuntimeError("jurnal ishlamadi")

    monkeypatch.setattr("vositalar.amallar.yoz", buzuq)
    with pytest.raises(RuntimeError):
        kochir(q, SON("4"), ofis, user)

    assert Taqsimot.objects.get().soni == SON("6")
    assert not TaqsimotHarakat.objects.exists()


def test_parallel_yaratilgan_nishon_amalxato(av, filial, ombor, ofis, user, monkeypatch):
    """Nishon qatorni qulflashdan keyin boshqa amal yaratgan bo'lsa (unikal kalit buzilishi) — 500 emas, AmalXato."""
    import vositalar.amallar as amallar

    qoldiq(av, filial, "6")
    q = qator(av, filial, "4", bolim=ombor)
    qator(av, filial, "2", bolim=ofis)  # nishon: qulflangan ro'yxatda «yo'q» deb ko'rsatiladi
    asl = amallar._qulfla

    def nishonsiz(qator_):
        manba, qulflangan = asl(qator_)
        return manba, [t for t in qulflangan if t.bolim_id != ofis.pk]

    monkeypatch.setattr(amallar, "_qulfla", nishonsiz)
    with pytest.raises(AmalXato, match="qayta urinib ko'ring"):
        kochir(q, SON("1"), ofis, user)
    q.refresh_from_db()
    assert q.soni == SON("4")
    assert jami(av, filial) == SON("6")


def test_kamaytir_kutilayotgan_chiqim_birliklarini_ayirmaydi_manfiy_qoldiq(av, filial, ombor, user, filial_yarat):
    from chiqimlar.models import ChiqimHujjat

    qoldiq(av, filial, "-3")
    qoldiq(av, filial_yarat("B"), "5")  # AV arxivga tushmasligi uchun umumiy qoldiq musbat
    q = qator(av, filial, "2", bolim=ombor)
    ChiqimHujjat.objects.create(
        hujjat_turi="Реализация", hujjat_raqami="1", hujjat_ref=uuid.uuid4(),
        sana=datetime(2026, 9, 10, tzinfo=dt_timezone.utc), av=av, filial=filial, soni=SON("2"), summa=SON("1"),
        taxmin_tur="sotildi",
    )
    with pytest.raises(AmalXato, match="kamaytirish shart emas"):
        kamaytir(q, SON("1"), user)
    q.refresh_from_db()
    assert q.soni == SON("2")


def test_kochir_sabab_va_izoh(av, filial, ombor, ofis, user):
    qoldiq(av, filial, 5)
    t = qator(av, filial, 5, bolim=ombor)
    kochir(t, SON("2"), ofis, user, sabab=Sabab.REVIZIYA, hujjat_izoh="RV-000001")
    h = TaqsimotHarakat.objects.get()
    assert h.sabab == "reviziya" and h.hujjat_izoh == "RV-000001"
