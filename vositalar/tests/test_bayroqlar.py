import uuid
from datetime import date
from decimal import Decimal

import pytest

from onec.models import AV, AVQoldiq, AVTuri, Xodim
from vositalar.bayroqlar import BAYROQLAR, bayroq_sonlari
from vositalar.models import AVKartochka, AVTuriSozlama, Bolim, Holat, Taqsimot

BUGUN = date(2026, 10, 17)
KALITLAR = {
    "inv_bosh", "inv_takror", "filial_rekvizit_bosh", "mos_emas", "bolimsiz", "molsiz", "ketgan_xodimda",
    "yorliq_yoq", "yorliq_almashtirish", "muddat_tugagan", "muddat_6oy", "chiqim_kutilmoqda",
}


@pytest.fixture
def filial_a(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def filial_b(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


_soni = iter(range(1, 10_000))


def av_yarat(filial=None, inv="INV", soni="1", qoldiq_filial=None, **kw):
    """AV; `filial` — filial_rekvizit; `qoldiq_filial` (yoki filial) da `soni` qoldiq (0 — arxiv)."""
    n = next(_soni)
    av = AV.objects.create(
        ref_1c=uuid.uuid4(), kod=str(n), nomi=f"AV {n}", inv_raqam=inv, filial_rekvizit=filial, **kw
    )
    joy = qoldiq_filial or filial
    if joy is not None:
        qoldiq(av, joy, soni)
    return av


def qoldiq(av, filial, soni):
    return AVQoldiq.objects.create(av=av, filial=filial, soni=Decimal(soni), summa=Decimal("100"))


def qator(av, filial, soni="1", bolim=None, mol=None):
    return Taqsimot.objects.create(
        av=av, filial=filial, bolim=bolim, mol=mol, holat=Holat.ISHLATILMOQDA, soni=Decimal(soni)
    )


def xodim(**kw):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Ali", **kw)


def royxat(kalit, user, bugun=BUGUN):
    return list(BAYROQLAR[kalit].so_rov(user, bugun))


def idlar(kalit, user, bugun=BUGUN):
    return {obyekt.pk for obyekt in royxat(kalit, user, bugun)}


def test_kalitlar_toplami():
    assert set(BAYROQLAR) == KALITLAR


def test_inv_bosh(hisobchi, filial_a):
    bosh = av_yarat(filial_a, inv="")
    bosh_joy = av_yarat(filial_a, inv="  \t ")
    normal = av_yarat(filial_a, inv="125")

    assert idlar("inv_bosh", hisobchi) == {bosh.pk, bosh_joy.pk}
    assert normal.pk not in idlar("inv_bosh", hisobchi)


def test_inv_takror_musbat_va_manfiy(hisobchi, filial_a):
    bir = av_yarat(filial_a, inv="125")
    ikki = av_yarat(filial_a, inv=" 125 ")
    yagona = av_yarat(filial_a, inv="126")
    bosh1 = av_yarat(filial_a, inv="")
    bosh2 = av_yarat(filial_a, inv="")

    assert idlar("inv_takror", hisobchi) == {bir.pk, ikki.pk}
    assert not {yagona.pk, bosh1.pk, bosh2.pk} & idlar("inv_takror", hisobchi)


def test_inv_takror_filial_ichida(hisobchi, filial_a, filial_b):
    a = av_yarat(filial_a, inv="7")
    b = av_yarat(filial_b, inv="7")
    assert idlar("inv_takror", hisobchi) == set()

    a2 = av_yarat(filial_a, inv="7")
    assert idlar("inv_takror", hisobchi) == {a.pk, a2.pk}
    assert b.pk not in idlar("inv_takror", hisobchi)


def test_inv_takror_arxiv_hisobga_olinmaydi(hisobchi, filial_a):
    av_yarat(filial_a, inv="9", soni="0")
    faol = av_yarat(filial_a, inv="9")

    assert faol.pk not in idlar("inv_takror", hisobchi)


def test_filial_rekvizit_bosh(hisobchi, filial_a):
    bosh = av_yarat(None, qoldiq_filial=filial_a)
    toldirilgan = av_yarat(filial_a)

    assert idlar("filial_rekvizit_bosh", hisobchi) == {bosh.pk}
    assert toldirilgan.pk not in idlar("filial_rekvizit_bosh", hisobchi)


def test_mos_emas(hisobchi, filial_a, filial_b):
    mos = av_yarat(filial_a, soni="3")
    qator(mos, filial_a, "3")
    kam = av_yarat(filial_a, soni="3")
    qator(kam, filial_a, "2")
    kop = av_yarat(filial_a, soni="3")
    qator(kop, filial_a, "4")
    ikkinchi_filial = av_yarat(filial_a, soni="2")
    qator(ikkinchi_filial, filial_a, "2")
    qoldiq(ikkinchi_filial, filial_b, "1")  # filial_b'da taqsimot yo'q

    assert idlar("mos_emas", hisobchi) == {kam.pk, kop.pk, ikkinchi_filial.pk}


def test_mos_emas_juft_boyicha_yigiladi(hisobchi, filial_a):
    av = av_yarat(filial_a, soni="2")
    qoldiq(av, filial_a, "1")  # bir juftning ikkinchi qatori (boshqa tashkilot): jami 3
    qator(av, filial_a, "1")
    qator(av, filial_a, "2", mol=xodim())

    assert idlar("mos_emas", hisobchi) == set()


def test_bolimsiz(hisobchi, filial_a):
    bolim = Bolim.objects.create(filial=filial_a, nomi="Savdo")
    av = av_yarat(filial_a, soni="2")
    bosh = qator(av, filial_a, "1")
    qator(av, filial_a, "1", bolim=bolim)

    assert [t.pk for t in royxat("bolimsiz", hisobchi)] == [bosh.pk]
    assert BAYROQLAR["bolimsiz"].model is Taqsimot


def test_bolimsiz_manfiy(hisobchi, filial_a):
    bolim = Bolim.objects.create(filial=filial_a, nomi="Savdo")
    av = av_yarat(filial_a)
    qator(av, filial_a, "1", bolim=bolim)

    assert royxat("bolimsiz", hisobchi) == []


def test_molsiz(hisobchi, filial_a):
    av = av_yarat(filial_a, soni="2")
    bosh = qator(av, filial_a, "1")
    qator(av, filial_a, "1", mol=xodim())

    assert [t.pk for t in royxat("molsiz", hisobchi)] == [bosh.pk]
    assert BAYROQLAR["molsiz"].model is Taqsimot


@pytest.mark.parametrize("maydon", ["ishdan_bushagan", "neaktiv", "onec_da_yoq"])
def test_ketgan_xodimda_musbat(hisobchi, filial_a, maydon):
    av = av_yarat(filial_a)
    t = qator(av, filial_a, "1", mol=xodim(**{maydon: True}))

    assert [x.pk for x in royxat("ketgan_xodimda", hisobchi)] == [t.pk]
    assert BAYROQLAR["ketgan_xodimda"].model is Taqsimot


def test_ketgan_xodimda_manfiy(hisobchi, filial_a):
    av = av_yarat(filial_a, soni="2")
    qator(av, filial_a, "1", mol=xodim())
    qator(av, filial_a, "1")  # MOL'siz — bu boshqa bayroq

    assert royxat("ketgan_xodimda", hisobchi) == []


def test_yorliq_yoq(hisobchi, filial_a):
    kartochkasiz = av_yarat(filial_a)
    bosh = av_yarat(filial_a)
    AVKartochka.objects.create(av=bosh, yorliq_kaliti="")
    nol = av_yarat(filial_a)
    AVKartochka.objects.create(av=nol, yorliq_kaliti=None)
    bor = av_yarat(filial_a)
    AVKartochka.objects.create(av=bor, yorliq_kaliti="DS|A|INV")

    assert idlar("yorliq_yoq", hisobchi) == {kartochkasiz.pk, bosh.pk, nol.pk}


def test_yorliq_almashtirish(hisobchi, filial_a):
    eski = av_yarat(filial_a, inv="125")
    AVKartochka.objects.create(av=eski, yorliq_kaliti="DS|A|124")
    joriy = av_yarat(filial_a, inv="126")
    AVKartochka.objects.create(av=joriy, yorliq_kaliti="DS|A|126")
    chop_etilmagan = av_yarat(filial_a, inv="127")
    AVKartochka.objects.create(av=chop_etilmagan, yorliq_kaliti=None)
    kalitsiz = av_yarat(filial_a, inv="")  # inv o'chirilgan: joriy kalit yo'q, eski yorliq yaroqsiz
    AVKartochka.objects.create(av=kalitsiz, yorliq_kaliti="DS|A|1")

    assert idlar("yorliq_almashtirish", hisobchi) == {eski.pk, kalitsiz.pk}


def test_kalit_bosh_joylarsiz(hisobchi, filial_yarat):
    filial = filial_yarat("07 ")
    av = av_yarat(filial, inv=" 125 ")
    AVKartochka.objects.create(av=av, yorliq_kaliti="DS|07|125")

    assert av.kalit == "DS|07|125"
    assert av.pk not in idlar("yorliq_almashtirish", hisobchi)


def test_kalit_none(filial_a):
    assert av_yarat(filial_a, inv="  ").kalit is None
    assert av_yarat(None, inv="1").kalit is None


def test_muddat_tugagan_va_6oy(hisobchi, filial_a):
    def av_muddat(sana, muddat):
        av = av_yarat(filial_a)
        AVKartochka.objects.create(av=av, ishga_tushgan_sana=sana, xizmat_muddati_oy=muddat)
        return av

    tugagan = av_muddat(date(2020, 1, 1), 12)  # tugash 2021-01-01
    aynan_bugun = av_muddat(date(2021, 10, 17), 60)  # tugash 2026-10-17
    olti_oyda = av_muddat(date(2022, 2, 17), 60)  # tugash 2027-02-17
    chegara = av_muddat(date(2022, 4, 17), 60)  # tugash 2027-04-17 = bugun + 6 oy
    uzoq = av_muddat(date(2022, 4, 18), 60)  # tugash 2027-04-18
    kelajak = av_muddat(date(2026, 1, 1), 60)
    muddatsiz = av_yarat(filial_a)
    AVKartochka.objects.create(av=muddatsiz, ishga_tushgan_sana=date(2020, 1, 1))
    sanasiz = av_yarat(filial_a)
    AVKartochka.objects.create(av=sanasiz, xizmat_muddati_oy=12)

    assert idlar("muddat_tugagan", hisobchi) == {tugagan.pk, aynan_bugun.pk}
    assert idlar("muddat_6oy", hisobchi) == {olti_oyda.pk, chegara.pk}
    assert not {uzoq.pk, kelajak.pk, muddatsiz.pk, sanasiz.pk} & (
        idlar("muddat_tugagan", hisobchi) | idlar("muddat_6oy", hisobchi)
    )


def test_muddat_tur_sozlamasidan(hisobchi, filial_a):
    turi = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="Mebel")
    AVTuriSozlama.objects.create(av_turi=turi, xizmat_muddati_oy=12)
    av = av_yarat(filial_a, turi=turi)
    AVKartochka.objects.create(av=av, ishga_tushgan_sana=date(2020, 1, 1))

    assert idlar("muddat_tugagan", hisobchi) == {av.pk}


def test_bayroqlar_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    a = av_yarat(filial_a, inv="")
    b = av_yarat(filial_b, inv="")
    ikkala = av_yarat(filial_a, inv="", soni="1")
    qoldiq(ikkala, filial_b, "1")
    ta = qator(a, filial_a)
    tb = qator(b, filial_b)

    assert idlar("inv_bosh", user_a) == {a.pk, ikkala.pk}
    assert b.pk not in idlar("inv_bosh", user_a)
    assert idlar("bolimsiz", user_a) == {ta.pk}
    assert tb.pk not in idlar("molsiz", user_a)
    assert idlar("molsiz", user_a) == {ta.pk}


def test_mos_emas_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    av = av_yarat(filial_a, soni="1")
    qator(av, filial_a, "1")
    qoldiq(av, filial_b, "1")  # mos emaslik faqat filial_b'da
    boshqa = av_yarat(filial_b, soni="1")

    assert idlar("mos_emas", user_a) == set()
    assert idlar("mos_emas", foydalanuvchi("admin")) == {av.pk, boshqa.pk}


def test_arxiv_bayroqlarda_yoq(hisobchi, filial_a, filial_b):
    arxiv = av_yarat(None, inv="", soni="0", qoldiq_filial=filial_a)
    qoldiq(arxiv, filial_b, "0")
    qator(arxiv, filial_a, "1")
    qator(arxiv, filial_a, "1", mol=xodim(ishdan_bushagan=True))
    AVKartochka.objects.create(
        av=arxiv, ishga_tushgan_sana=date(2020, 1, 1), xizmat_muddati_oy=12, yorliq_kaliti="DS|X|Y"
    )

    for kalit in BAYROQLAR:
        topilgan = {o.av_id if isinstance(o, Taqsimot) else o.pk for o in royxat(kalit, hisobchi)}
        assert arxiv.pk not in topilgan, kalit
    assert bayroq_sonlari(hisobchi, BUGUN) == dict.fromkeys(KALITLAR, 0)


def test_manfiy_qoldiq_bayroqlarda_yoq(hisobchi, filial_a):
    av_yarat(filial_a, inv="", soni="-1")

    assert idlar("inv_bosh", hisobchi) == set()


def test_bayroq_sonlari(hisobchi, filial_a):
    av = av_yarat(filial_a, inv="", soni="2")
    qator(av, filial_a, "1")
    qator(av, filial_a, "1", mol=xodim(neaktiv=True))
    toza = av_yarat(filial_a, inv="5")
    AVKartochka.objects.create(av=toza, yorliq_kaliti="DS|A|5")
    qator(toza, filial_a, "1", bolim=Bolim.objects.create(filial=filial_a, nomi="Savdo"), mol=xodim())

    sonlar = bayroq_sonlari(hisobchi, BUGUN)

    assert set(sonlar) == KALITLAR
    assert sonlar["inv_bosh"] == 1
    assert sonlar["bolimsiz"] == 2  # ikkala qator ham bo'limsiz
    assert sonlar["molsiz"] == 1
    assert sonlar["ketgan_xodimda"] == 1
    assert sonlar["yorliq_yoq"] == 1
    assert sonlar["yorliq_almashtirish"] == 0
    assert sonlar["mos_emas"] == 0
    assert sonlar["filial_rekvizit_bosh"] == 0
    assert sonlar["inv_takror"] == 0
    assert sonlar["muddat_tugagan"] == sonlar["muddat_6oy"] == 0


@pytest.mark.django_db
def test_qoldiq_bilan_qatorlarni_kopaytirmaydi(filial_a, filial_b):
    av = av_yarat(filial_a, soni="2")
    qoldiq(av, filial_a, "3")
    qoldiq(av, filial_b, "1")
    qator(av, filial_a, "5")
    qator(av, filial_b, "1")
    AVKartochka.objects.create(av=av)

    qs = AV.objects.qoldiq_bilan()
    assert qs.count() == 1
    obyekt = qs.get()
    assert obyekt.jami_soni == Decimal("6")
    assert obyekt.jami_summa == Decimal("300")


def test_faol_va_arxiv(filial_a):
    faol = av_yarat(filial_a, soni="1")
    nol = av_yarat(filial_a, soni="0")
    qoldiqsiz = av_yarat(None)
    manfiy = av_yarat(filial_a, soni="-2")

    assert set(AV.objects.faol()) == {faol}
    assert set(AV.objects.arxiv()) == {nol, qoldiqsiz, manfiy}
    assert AV.objects.qoldiq_bilan().get(pk=qoldiqsiz.pk).jami_soni == 0


# ---------- filial cheklovi: qolgan bayroqlar ----------

def test_ketgan_xodimda_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    ketgan = xodim(ishdan_bushagan=True)
    a = av_yarat(filial_a)
    b = av_yarat(filial_b)
    ta = qator(a, filial_a, "1", mol=ketgan)
    qator(b, filial_b, "1", mol=ketgan)

    assert idlar("ketgan_xodimda", user_a) == {ta.pk}
    assert len(royxat("ketgan_xodimda", foydalanuvchi("admin"))) == 2


def test_yorliq_bayroqlari_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    yoq_a, yoq_b = av_yarat(filial_a), av_yarat(filial_b)
    eski_a = av_yarat(filial_a, inv="125")
    AVKartochka.objects.create(av=eski_a, yorliq_kaliti="DS|A|124")
    eski_b = av_yarat(filial_b, inv="125")
    AVKartochka.objects.create(av=eski_b, yorliq_kaliti="DS|B|124")

    assert idlar("yorliq_yoq", user_a) == {yoq_a.pk}
    assert idlar("yorliq_almashtirish", user_a) == {eski_a.pk}
    admin = foydalanuvchi("admin")
    assert {yoq_a.pk, yoq_b.pk} <= idlar("yorliq_yoq", admin)
    assert idlar("yorliq_almashtirish", admin) == {eski_a.pk, eski_b.pk}


def test_muddat_bayroqlari_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])

    def av_muddat(filial, sana):
        av = av_yarat(filial)
        AVKartochka.objects.create(av=av, ishga_tushgan_sana=sana, xizmat_muddati_oy=60)
        return av

    tugagan_a, tugagan_b = av_muddat(filial_a, date(2020, 1, 1)), av_muddat(filial_b, date(2020, 1, 1))
    olti_a, olti_b = av_muddat(filial_a, date(2022, 2, 17)), av_muddat(filial_b, date(2022, 2, 17))

    assert idlar("muddat_tugagan", user_a) == {tugagan_a.pk}
    assert idlar("muddat_6oy", user_a) == {olti_a.pk}
    admin = foydalanuvchi("admin")
    assert idlar("muddat_tugagan", admin) == {tugagan_a.pk, tugagan_b.pk}
    assert idlar("muddat_6oy", admin) == {olti_a.pk, olti_b.pk}


def test_inv_takror_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    a1, a2 = av_yarat(filial_a, inv="7"), av_yarat(filial_a, inv="7")
    b1, b2 = av_yarat(filial_b, inv="8"), av_yarat(filial_b, inv="8")

    assert idlar("inv_takror", user_a) == {a1.pk, a2.pk}
    assert idlar("inv_takror", foydalanuvchi("admin")) == {a1.pk, a2.pk, b1.pk, b2.pk}


# --- Kutilayotgan 1C chiqimi ---


def chiqim(av, filial, soni="1", holat="kutilmoqda"):
    from django.utils import timezone

    from chiqimlar.models import ChiqimHujjat

    return ChiqimHujjat.objects.create(
        hujjat_turi="РеализацияТоваровУслуг", hujjat_raqami="7", hujjat_ref=uuid.uuid4(),
        sana=timezone.now(), av=av, filial=filial, soni=Decimal(soni), summa=Decimal("100"),
        holat=holat, taxmin_tur="sotildi",
    )


def test_mos_emas_K_bilan(hisobchi, filial_a):
    mos = av_yarat(filial_a, soni="4")
    qator(mos, filial_a, "6")
    chiqim(mos, filial_a, "2")  # 4 + 2 = 6 — mos
    kam = av_yarat(filial_a, soni="4")
    qator(kam, filial_a, "4")
    chiqim(kam, filial_a, "2")  # 4 < 4 + 2 — mos emas
    bekor = av_yarat(filial_a, soni="4")
    qator(bekor, filial_a, "6")
    chiqim(bekor, filial_a, "2", holat="bekor")  # bekor K'ga kirmaydi — mos emas

    assert idlar("mos_emas", hisobchi) == {kam.pk, bekor.pk}


def test_mos_emas_K_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    av = av_yarat(filial_a, soni="1")
    qator(av, filial_a, "1")
    qoldiq(av, filial_b, "1")
    qator(av, filial_b, "2")
    chiqim(av, filial_b, "1")  # filial_b: 1 + 1 = 2 — mos

    assert idlar("mos_emas", user_a) == set()
    assert idlar("mos_emas", foydalanuvchi("admin")) == set()


def test_bayroq_chiqim_kutilmoqda_filial_cheklovi(foydalanuvchi, filial_a, filial_b):
    user_a = foydalanuvchi("hisobchi", [filial_a])
    av = av_yarat(filial_a, soni="1")
    qoldiq(av, filial_b, "1")
    a = chiqim(av, filial_a)
    b = chiqim(av, filial_b)
    chiqim(av, filial_a, holat="bekor")
    chiqim(av, filial_a, holat="tasdiqlangan")

    assert BAYROQLAR["chiqim_kutilmoqda"].nomi == "1C chiqimi kutilmoqda"
    assert idlar("chiqim_kutilmoqda", user_a) == {a.pk}
    assert idlar("chiqim_kutilmoqda", foydalanuvchi("admin")) == {a.pk, b.pk}
    assert bayroq_sonlari(user_a, BUGUN)["chiqim_kutilmoqda"] == 1


def test_av_royxati_bayroq_chiqim_kutilmoqda(foydalanuvchi, filial_a, filial_b):
    from vositalar.filtrlar import av_filtrla

    user_a = foydalanuvchi("hisobchi", [filial_a])
    av = av_yarat(filial_a, soni="2")
    chiqim(av, filial_a)
    chiqim(av, filial_a)  # bir AV'da ikki chiqim — ro'yxatda bir marta
    boshqa = av_yarat(filial_b, soni="1")
    chiqim(boshqa, filial_b)
    av_yarat(filial_a, soni="1")  # chiqimsiz

    qs = av_filtrla(AV.objects.all(), {"bayroq": "chiqim_kutilmoqda"}, user_a)
    assert list(qs.values_list("pk", flat=True)) == [av.pk]
    qs = av_filtrla(AV.objects.all(), {"bayroq": "chiqim_kutilmoqda"}, foydalanuvchi("admin"))
    assert set(qs.values_list("pk", flat=True)) == {av.pk, boshqa.pk}
