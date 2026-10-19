import uuid
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import pytest

from chiqimlar.models import ChiqimHujjat
from chiqimlar.servis import ChiqimXato, taqsimot_qatorlari, tasdiqla
from jurnal.models import Jurnal
from onec.models import AV, AVQoldiq
from vositalar.models import Bolim, Holat, Taqsimot, TaqsimotHarakat
from vositalar.moslash import farq, moslashtir

pytestmark = pytest.mark.django_db

SON = Decimal
SANA = datetime(2026, 9, 10, 12, 0, tzinfo=dt_tz.utc)
Sabab = TaqsimotHarakat.Sabab


@pytest.fixture
def av():
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def fb(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def user(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def prixod(fa):
    return Bolim.objects.create(filial=fa, nomi="Prixodxona")


@pytest.fixture
def ofis(fa):
    return Bolim.objects.create(filial=fa, nomi="Ofis")


@pytest.fixture
def b_ombor(fb):
    return Bolim.objects.create(filial=fb, nomi="B ombor")


def qoldiq(av, filial, soni):
    return AVQoldiq.objects.create(av=av, filial=filial, soni=SON(soni), summa=SON("100"))


def qator(av, filial, soni, bolim=None, holat=Holat.ISHLATILMOQDA):
    return Taqsimot.objects.create(av=av, filial=filial, bolim=bolim, holat=holat, soni=SON(soni))


def chiqim(av, filial, soni, taxmin="sotildi"):
    return ChiqimHujjat.objects.create(
        hujjat_turi="Реализация", hujjat_raqami="17", hujjat_ref=uuid.uuid4(), sana=SANA,
        av=av, filial=filial, soni=SON(soni), summa=SON("100"), taxmin_tur=taxmin,
    )


def holat_snapshot():
    return sorted(
        (t.av_id, t.filial_id, t.bolim_id, t.mol_id, t.holat, t.soni) for t in Taqsimot.objects.all()
    )


def test_bitta_qator_toliq_sotildi(av, fa, prixod, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1")

    tasdiqla(c, "sotildi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), izoh="Xaridorga")

    assert not Taqsimot.objects.filter(pk=q.pk).exists()
    h = TaqsimotHarakat.objects.get()
    assert (h.sabab, h.soni, h.eski_bolim, h.kim, h.hujjat_izoh) == (
        Sabab.SOTILDI, SON("1"), prixod, user, "Реализация 17"
    )
    assert h.yangi_bolim is None and h.yangi_holat == ""
    c.refresh_from_db()
    assert (c.holat, c.tur, c.izoh, c.kim, c.qabul_filial) == ("tasdiqlangan", "sotildi", "Xaridorga", user, None)
    assert c.qachon is not None
    assert Jurnal.objects.filter(obyekt_turi="chiqimlar.chiqimhujjat", maydon="holat", yangi="tasdiqlangan").exists()
    assert Jurnal.objects.filter(obyekt_turi="vositalar.taqsimot", maydon="soni", eski="1.000", yangi="0.000").exists()
    assert farq(av, fa) == 0


def test_guruh_qisman_ikki_qatordan(av, fa, prixod, ofis, user):
    qoldiq(av, fa, "3")
    p = qator(av, fa, "4", bolim=prixod)
    o = qator(av, fa, "2", bolim=ofis)
    c = chiqim(av, fa, "3")

    tasdiqla(c, "hisobdan_chiqarildi", {p.pk: SON("2"), o.pk: SON("1")}, user, kutilgan_soni=SON("3"))

    p.refresh_from_db()
    o.refresh_from_db()
    assert (p.soni, o.soni) == (SON("2"), SON("1"))
    assert set(TaqsimotHarakat.objects.values_list("sabab", flat=True)) == {Sabab.HISOBDAN_CHIQARILDI}
    assert TaqsimotHarakat.objects.count() == 2
    assert farq(av, fa) == 0


def test_nol_qiymatlar_etiborsiz(av, fa, prixod, ofis, user):
    qoldiq(av, fa, "1")
    p = qator(av, fa, "1", bolim=prixod)
    o = qator(av, fa, "1", bolim=ofis)
    c = chiqim(av, fa, "1")

    tasdiqla(c, "sotildi", {p.pk: SON("1"), o.pk: SON("0")}, user, kutilgan_soni=SON("1"))

    assert list(Taqsimot.objects.values_list("pk", flat=True)) == [o.pk]


def _rad(c, *args, xabar, **kwargs):
    oldin = holat_snapshot()
    with pytest.raises(ChiqimXato) as xato:
        tasdiqla(c, *args, **kwargs)
    assert xabar in str(xato.value)
    assert holat_snapshot() == oldin
    c.refresh_from_db()
    assert c.holat == "kutilmoqda"
    assert TaqsimotHarakat.objects.count() == 0


def test_yigindi_teng_bolmasa_rad(av, fa, prixod, ofis, user):
    qoldiq(av, fa, "3")
    p = qator(av, fa, "4", bolim=prixod)
    o = qator(av, fa, "2", bolim=ofis)
    c = chiqim(av, fa, "3")
    _rad(c, "sotildi", {p.pk: SON("1"), o.pk: SON("1")}, user, kutilgan_soni=SON("3"), xabar="teng")


def test_boshqa_av_qatori_rad(av, fa, prixod, user):
    boshqa = AV.objects.create(ref_1c=uuid.uuid4(), kod="2", nomi="Kursi")
    qoldiq(av, fa, "0")
    qator(av, fa, "1", bolim=prixod)
    begona = qator(boshqa, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1")
    _rad(c, "sotildi", {begona.pk: SON("1")}, user, kutilgan_soni=SON("1"), xabar="topilmadi")


def test_soni_qatordan_kop_rad(av, fa, prixod, ofis, user):
    qoldiq(av, fa, "1")
    p = qator(av, fa, "1", bolim=prixod)
    qator(av, fa, "2", bolim=ofis)
    c = chiqim(av, fa, "2")
    _rad(c, "sotildi", {p.pk: SON("2")}, user, kutilgan_soni=SON("2"), xabar="oshib")


def test_manfiy_son_rad(av, fa, prixod, ofis, user):
    qoldiq(av, fa, "1")
    p = qator(av, fa, "1", bolim=prixod)
    o = qator(av, fa, "2", bolim=ofis)
    c = chiqim(av, fa, "1")
    _rad(c, "sotildi", {o.pk: SON("2"), p.pk: SON("-1")}, user, kutilgan_soni=SON("1"), xabar="noldan")


def test_otkazish_b_filial_majburiy_va_A_emas(av, fa, prixod, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1", taxmin="otkazish")
    _rad(c, "otkazish", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), xabar="Qabul qiluvchi filialni")
    _rad(c, "otkazish", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), qabul_filial=fa, xabar="boshqa")


def test_notogri_tur_rad(av, fa, prixod, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1")
    _rad(c, "yoqoldi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), xabar="turini")


def test_otkazish_b_ga_joylash(av, fa, fb, prixod, b_ombor, user):
    qoldiq(av, fa, "0")
    qoldiq(av, fb, "3")
    q = qator(av, fa, "3", bolim=prixod)
    qator(av, fb, "3")  # B'ga Поступление bilan kelgan, taqsimlanmagan
    c = chiqim(av, fa, "3", taxmin="otkazish")

    tasdiqla(
        c, "otkazish", {q.pk: SON("3")}, user, kutilgan_soni=SON("3"),
        qabul_filial=fb, b_bolim=b_ombor, b_holat=Holat.ZAXIRADA,
    )

    assert not Taqsimot.objects.filter(filial=fa).exists()
    b = Taqsimot.objects.get(filial=fb)
    assert (b.bolim, b.holat, b.soni) == (b_ombor, Holat.ZAXIRADA, SON("3"))
    assert TaqsimotHarakat.objects.filter(filial=fa, sabab=Sabab.OTKAZILDI).count() == 1
    c.refresh_from_db()
    assert (c.tur, c.qabul_filial) == ("otkazish", fb)
    assert farq(av, fa) == 0 and farq(av, fb) == 0


def test_otkazish_b_qisman_joylash(av, fa, fb, prixod, b_ombor, user):
    # B'da taqsimlanmagan 5 (boshqa kirim ham bor), chiqim 2 -> faqat 2 tasi ko'chadi.
    qoldiq(av, fa, "0")
    qoldiq(av, fb, "5")
    q = qator(av, fa, "2", bolim=prixod)
    qator(av, fb, "5")
    c = chiqim(av, fa, "2", taxmin="otkazish")

    tasdiqla(c, "otkazish", {q.pk: SON("2")}, user, kutilgan_soni=SON("2"), qabul_filial=fb, b_bolim=b_ombor)

    assert Taqsimot.objects.get(filial=fb, bolim=None).soni == SON("3")
    assert Taqsimot.objects.get(filial=fb, bolim=b_ombor).holat == Holat.ISHLATILMOQDA


def test_otkazish_b_bolim_boshqa_filial_rad(av, fa, fb, prixod, user):
    qoldiq(av, fa, "0")
    qoldiq(av, fb, "1")
    q = qator(av, fa, "1", bolim=prixod)
    qator(av, fb, "1")
    c = chiqim(av, fa, "1", taxmin="otkazish")
    _rad(
        c, "otkazish", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), qabul_filial=fb, b_bolim=prixod,
        xabar="qabul qiluvchi filialga",
    )


def test_otkazish_b_da_taqsimlanmagan_yoq(av, fa, fb, prixod, b_ombor, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1", taxmin="otkazish")

    tasdiqla(c, "otkazish", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), qabul_filial=fb, b_bolim=b_ombor)

    assert not Taqsimot.objects.exists()
    c.refresh_from_db()
    assert c.holat == "tasdiqlangan"


def test_soni_ozgargan_rad(av, fa, prixod, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "2", bolim=prixod)
    c = chiqim(av, fa, "2")
    _rad(c, "sotildi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), xabar="sahifani yangilang")


def test_qayta_tasdiqlash_rad(av, fa, prixod, user):
    qoldiq(av, fa, "1")
    q = qator(av, fa, "2", bolim=prixod)
    c = chiqim(av, fa, "1")
    tasdiqla(c, "sotildi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"))
    oldin = holat_snapshot()
    with pytest.raises(ChiqimXato, match="allaqachon tasdiqlangan"):
        tasdiqla(c, "sotildi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"))
    assert holat_snapshot() == oldin


def test_arxiv_av_tasdiqlanadi(av, fa, prixod, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1")

    tasdiqla(c, "sotildi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"))

    assert not Taqsimot.objects.exists()


def test_sinxrondan_keyin_invariant(av, fa, fb, prixod, ofis, b_ombor, user):
    qoldiq(av, fa, "1")
    qoldiq(av, fb, "3")
    p = qator(av, fa, "3", bolim=prixod)
    o = qator(av, fa, "1", bolim=ofis)
    qator(av, fb, "3")
    c = chiqim(av, fa, "3", taxmin="otkazish")
    boshida = holat_snapshot()
    moslashtir()  # K hisobga olinadi: hech narsa o'zgarmaydi
    assert holat_snapshot() == boshida

    tasdiqla(
        c, "otkazish", {p.pk: SON("2"), o.pk: SON("1")}, user, kutilgan_soni=SON("3"),
        qabul_filial=fb, b_bolim=b_ombor, b_holat=Holat.TAMIRDA,
    )
    oldin = holat_snapshot()
    harakatlar = TaqsimotHarakat.objects.count()

    stat = moslashtir()

    assert holat_snapshot() == oldin
    assert TaqsimotHarakat.objects.count() == harakatlar
    assert (stat["kopaydi"], stat["kamaydi"], stat["nolga_tushdi"], stat["mos_emas"]) == (0, 0, 0, 0)


def test_invariant_buzilsa_rad(av, fa, prixod, user):
    # Avvaldan buzilgan holat: 1C 5, taqsimot 4 (yetishmaydi) -> tasdiqlashdan keyin ham kam qoladi.
    qoldiq(av, fa, "5")
    q = qator(av, fa, "4", bolim=prixod)
    c = chiqim(av, fa, "1")
    _rad(c, "sotildi", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), xabar="1C qoldig'idan kam")


def test_taqsimot_qatorlari(av, fa, fb, prixod, ofis):
    p = qator(av, fa, "1", bolim=prixod)
    o = qator(av, fa, "1", bolim=ofis)
    qator(av, fb, "1")
    c = chiqim(av, fa, "1")
    assert [t.pk for t in taqsimot_qatorlari(c)] == [p.pk, o.pk]


def test_tasdiqla_joylangan_sonni_qaytaradi(av, fa, fb, prixod, b_ombor, user):
    qoldiq(av, fa, "0")
    qoldiq(av, fb, "5")
    q = qator(av, fa, "2", bolim=prixod)
    qator(av, fb, "1")  # B'da faqat 1 ta taqsimlanmagan, chiqim 2
    c = chiqim(av, fa, "2", taxmin="otkazish")
    assert tasdiqla(c, "otkazish", {q.pk: SON("2")}, user, kutilgan_soni=SON("2"), qabul_filial=fb, b_bolim=b_ombor) == SON("1")


def test_tasdiqla_joylash_yoq_nol_qaytaradi(av, fa, fb, prixod, b_ombor, user):
    qoldiq(av, fa, "0")
    q = qator(av, fa, "1", bolim=prixod)
    c = chiqim(av, fa, "1", taxmin="otkazish")
    assert tasdiqla(c, "otkazish", {q.pk: SON("1")}, user, kutilgan_soni=SON("1"), qabul_filial=fb, b_bolim=b_ombor) == 0
    q2 = qator(av, fa, "1", bolim=prixod)
    c2 = chiqim(av, fa, "1", taxmin="sotildi")
    qoldiq(av, fa, "0")
    assert tasdiqla(c2, "sotildi", {q2.pk: SON("1")}, user, kutilgan_soni=SON("1")) == 0
