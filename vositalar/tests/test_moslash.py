import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from jurnal.models import Jurnal
from onec.models import AV, AVQoldiq, Harakat1C, Tashkilot
from vositalar.models import AVKartochka, Bolim, Holat, Taqsimot, TaqsimotHarakat
from vositalar.moslash import MoslashXato, farq, moslashtir

SON = Decimal


@pytest.fixture
def av(db):
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


@pytest.fixture
def filial_a(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def filial_b(filial_yarat):
    return filial_yarat("B")


def qoldiq(av, filial, soni, tashkilot=None):
    return AVQoldiq.objects.create(
        av=av, filial=filial, tashkilot=tashkilot, soni=SON(soni), summa=SON("100")
    )


def qator(av, filial, soni, bolim=None, holat=Holat.ISHLATILMOQDA):
    return Taqsimot.objects.create(av=av, filial=filial, bolim=bolim, holat=holat, soni=SON(soni))


def taqsimlanmagan(av, filial):
    return Taqsimot.objects.filter(
        av=av, filial=filial, bolim=None, mol=None, holat=Holat.ISHLATILMOQDA
    ).first()


def harakat1c(av, filial, vid, sana, turi="Kirim", raqam="1"):
    return Harakat1C.objects.create(
        sana=sana, hujjat_turi=turi, hujjat_raqami=raqam, hujjat_ref=uuid.uuid4(),
        av=av, filial=filial, vid=vid, soni=SON("1"), summa=SON("1"),
    )


def test_yangi_av_taqsimlanmagan(av, filial_a):
    qoldiq(av, filial_a, "20")

    stat = moslashtir()

    qatorlar = list(Taqsimot.objects.all())
    assert len(qatorlar) == 1
    q = qatorlar[0]
    assert (q.bolim, q.mol, q.holat, q.soni) == (None, None, Holat.ISHLATILMOQDA, SON("20"))
    assert AVKartochka.objects.filter(av=av).exists()
    assert stat["yangi_kartochka"] == 1
    assert stat["kopaydi"] == 1
    assert farq(av, filial_a) == 0
    h = TaqsimotHarakat.objects.get()
    assert h.sabab == TaqsimotHarakat.Sabab.ONEC_KOPAYDI and h.kim is None and h.soni == SON("20")
    assert h.yangi_holat == Holat.ISHLATILMOQDA
    j = Jurnal.objects.get(obyekt_turi="vositalar.taqsimot")
    assert j.kim is None and j.kim_nomi == "1C sinxron" and j.maydon == "soni"
    assert (SON(j.eski), SON(j.yangi)) == (0, 20)


def test_kopaydi(av, filial_a):
    zal = Bolim.objects.create(filial=filial_a, nomi="Zal")
    qoldiq(av, filial_a, "25")
    qator(av, filial_a, "5")
    ombor = qator(av, filial_a, "15", bolim=zal)
    AVKartochka.objects.create(av=av)

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a).soni == SON("10")
    ombor.refresh_from_db()
    assert ombor.soni == SON("15")
    assert stat["kopaydi"] == 1 and stat["yangi_kartochka"] == 0
    assert TaqsimotHarakat.objects.get().soni == SON("5")


def test_kamaydi_taqsimlanmagandan_yetadi(av, filial_a):
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    qoldiq(av, filial_a, "18")
    qator(av, filial_a, "3")
    qator(av, filial_a, "17", bolim=ombor)

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a).soni == SON("1")
    assert Taqsimot.objects.get(bolim=ombor).soni == SON("17")
    assert farq(av, filial_a) == 0
    assert stat["kamaydi"] == 1 and stat["mos_emas"] == 0
    h = TaqsimotHarakat.objects.get()
    assert h.sabab == TaqsimotHarakat.Sabab.ONEC_KAMAYDI and h.soni == SON("2") and h.eski_holat == Holat.ISHLATILMOQDA


def test_kamaydi_yetmaydi(av, filial_a):
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    qoldiq(av, filial_a, "15")
    qator(av, filial_a, "20", bolim=ombor)

    stat = moslashtir()

    assert Taqsimot.objects.get().soni == SON("20")
    assert farq(av, filial_a) == -5
    assert stat["mos_emas"] == 1 and stat["kamaydi"] == 0
    assert not TaqsimotHarakat.objects.exists()


def test_kamaydi_qisman_taqsimlanmagandan(av, filial_a):
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    qoldiq(av, filial_a, "15")
    qator(av, filial_a, "2")
    qator(av, filial_a, "18", bolim=ombor)

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a) is None
    assert farq(av, filial_a) == -3
    assert stat["kamaydi"] == 1 and stat["mos_emas"] == 1
    assert TaqsimotHarakat.objects.get().soni == SON("2")


def test_qisman_filial_otkazma(av, filial_a, filial_b):
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    qoldiq(av, filial_a, "15")
    qoldiq(av, filial_b, "5")
    qator(av, filial_a, "20", bolim=ombor)

    stat = moslashtir()

    assert farq(av, filial_a) == -5
    assert Taqsimot.objects.get(filial=filial_a).soni == SON("20")
    assert taqsimlanmagan(av, filial_b).soni == SON("5")
    assert farq(av, filial_b) == 0
    assert stat["mos_emas"] == 1 and stat["kopaydi"] == 1


def test_filial_nolga_tushdi(av, filial_a, filial_b):
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    qoldiq(av, filial_b, "4")
    qator(av, filial_a, "3")
    qator(av, filial_a, "7", bolim=ombor, holat=Holat.NOSOZ)
    qator(av, filial_b, "4")

    stat = moslashtir()

    assert not Taqsimot.objects.filter(filial=filial_a).exists()
    assert Taqsimot.objects.filter(filial=filial_b).count() == 1
    assert stat["nolga_tushdi"] == 1
    harakatlar = TaqsimotHarakat.objects.filter(filial=filial_a)
    assert harakatlar.count() == 2
    assert {h.sabab for h in harakatlar} == {TaqsimotHarakat.Sabab.ONEC_NOLGA_TUSHDI}
    assert sorted(h.soni for h in harakatlar) == [SON("3"), SON("7")]
    nosoz = harakatlar.get(soni=SON("7"))
    assert (nosoz.eski_bolim, nosoz.eski_holat, nosoz.yangi_holat) == (ombor, Holat.NOSOZ, "")
    jurnallar = Jurnal.objects.filter(obyekt_turi="vositalar.taqsimot")
    assert sorted((SON(j.eski), SON(j.yangi)) for j in jurnallar) == [(3, 0), (7, 0)]


def test_qoldiq_nol_yoki_yoq(av, filial_a, filial_b):
    qoldiq(av, filial_a, "0")
    qator(av, filial_a, "3")
    qator(av, filial_b, "2")  # qoldiq qatori umuman yo'q

    stat = moslashtir()

    assert not Taqsimot.objects.exists()
    assert stat["nolga_tushdi"] == 2 and stat["mos_emas"] == 0


def test_bir_nechta_tashkilot_qoldigi_yigiladi(av, filial_a):
    t1 = Tashkilot.objects.create(ref_1c=uuid.uuid4(), nomi="T1")
    t2 = Tashkilot.objects.create(ref_1c=uuid.uuid4(), nomi="T2")
    qoldiq(av, filial_a, "6", tashkilot=t1)
    qoldiq(av, filial_a, "4", tashkilot=t2)

    moslashtir()

    assert Taqsimot.objects.get().soni == SON("10")
    assert farq(av, filial_a) == 0


def test_hujjat_izoh_oxirgi_harakatdan(av, filial_a, filial_b):
    qoldiq(av, filial_a, "5")
    qoldiq(av, filial_b, "1")
    harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 1, 1)), "Kirim", "11")
    harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 3, 1)), "Ko'chirish", "22")
    harakat1c(av, filial_b, "kirim", timezone.make_aware(datetime(2026, 4, 1)), "Boshqa", "99")

    moslashtir()

    assert TaqsimotHarakat.objects.get(filial=filial_a).hujjat_izoh == "Ko'chirish 22"
    assert TaqsimotHarakat.objects.get(filial=filial_b).hujjat_izoh == "Boshqa 99"


def test_hujjat_izoh_sonni_ozgartirmagan_harakat_hisobga_olinmaydi(av, filial_a):
    """ПереоценкаОС (soni 0) keyinroq bo'lsa ham sabab — sonni o'zgartirgan oxirgi hujjat."""
    qoldiq(av, filial_a, "1")
    harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 1, 1)), "ПоступлениеОС", "11")
    qayta = harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 9, 30)), "ПереоценкаОС", "12")
    Harakat1C.objects.filter(pk=qayta.pk).update(soni=SON("0"))

    moslashtir()

    assert TaqsimotHarakat.objects.get().hujjat_izoh == "ПоступлениеОС 11"


def test_hujjat_izoh_faqat_soni_nol_harakat_bolsa_bosh(av, filial_a):
    qoldiq(av, filial_a, "1")
    qayta = harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 9, 30)), "ПереоценкаОС", "12")
    Harakat1C.objects.filter(pk=qayta.pk).update(soni=SON("0"))

    moslashtir()

    assert TaqsimotHarakat.objects.get().hujjat_izoh == ""


def test_hujjat_izoh_harakat_bolmasa_bosh(av, filial_a):
    qoldiq(av, filial_a, "5")

    moslashtir()

    assert TaqsimotHarakat.objects.get().hujjat_izoh == ""


def test_ishga_tushgan_sana_birinchi_kirim(av, filial_a):
    boshqa = AV.objects.create(ref_1c=uuid.uuid4(), kod="2", nomi="Stul")
    qoldiq(av, filial_a, "1")
    harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 5, 10, 23, 30)))
    harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 2, 3, 0, 30)))
    harakat1c(av, filial_a, "chiqim", timezone.make_aware(datetime(2025, 1, 1)))
    AVKartochka.objects.create(av=boshqa, ishga_tushgan_sana=date(2020, 1, 1))
    harakat1c(boshqa, filial_a, "kirim", timezone.make_aware(datetime(2026, 6, 1)))

    moslashtir()

    assert av.kartochka.ishga_tushgan_sana == date(2026, 2, 3)
    boshqa.kartochka.refresh_from_db()
    assert boshqa.kartochka.ishga_tushgan_sana == date(2020, 1, 1)


def test_ishga_tushgan_sana_kirim_yoq(av):
    moslashtir()

    assert av.kartochka.ishga_tushgan_sana is None


def test_nol_qoldiqli_av_ham_kartochka_oladi(av):
    stat = moslashtir()

    assert AVKartochka.objects.filter(av=av).exists()
    assert stat["yangi_kartochka"] == 1
    assert not Taqsimot.objects.exists()


def test_takroriy_moslash_idempotent(av, filial_a, filial_b):
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    boshqa = AV.objects.create(ref_1c=uuid.uuid4(), kod="2", nomi="Stul")
    qoldiq(av, filial_a, "15")
    qoldiq(av, filial_b, "5")
    qator(av, filial_a, "2")
    qator(av, filial_a, "20", bolim=ombor)
    qator(boshqa, filial_a, "3")
    harakat1c(av, filial_b, "kirim", timezone.make_aware(datetime(2026, 5, 1)))

    birinchi = moslashtir()
    assert birinchi["kamaydi"] == 1 and birinchi["kopaydi"] == 1 and birinchi["nolga_tushdi"] == 1

    def holat():
        return (
            sorted(Taqsimot.objects.values_list("av_id", "filial_id", "bolim_id", "soni")),
            TaqsimotHarakat.objects.count(),
            Jurnal.objects.count(),
            AVKartochka.objects.count(),
        )

    oldin = holat()

    ikkinchi = moslashtir()

    assert ikkinchi == {
        "yangi_kartochka": 0, "kopaydi": 0, "kamaydi": 0, "nolga_tushdi": 0, "mos_emas": 1,
    }
    assert holat() == oldin


def test_ishga_tushgan_sana_jurnalga_yoziladi(av, filial_a):
    qoldiq(av, filial_a, "1")
    harakat1c(av, filial_a, "kirim", timezone.make_aware(datetime(2026, 2, 3, 10, 0)))

    moslashtir()
    moslashtir()

    j = Jurnal.objects.get(obyekt_turi="vositalar.avkartochka")
    assert j.kim is None and j.kim_nomi == "1C sinxron"
    assert (j.obyekt_id, j.maydon, j.eski, j.yangi) == (str(av.kartochka.pk), "ishga_tushgan_sana", "", "2026-02-03")


def test_invariant_buzilsa_xato_va_rollback(av, filial_a, monkeypatch):
    qoldiq(av, filial_a, "5")
    monkeypatch.setattr("vositalar.moslash._kopaydi", lambda *args, **kw: None)

    with pytest.raises(MoslashXato, match="invarianti"):
        moslashtir()

    # moslashtir() o'z atomic blokida: kartochka ham rollback bo'lgan.
    assert not AVKartochka.objects.exists() and not Taqsimot.objects.exists()


def test_taqsimot_qatorlari_qulflanadi(av, filial_a):
    """Taqsimot qatorlari `select_for_update` bilan o'qiladi (spec §8)."""
    qoldiq(av, filial_a, "5")
    qator(av, filial_a, "2")

    with CaptureQueriesContext(connection) as ctx:
        moslashtir()
    sorovlar = [q["sql"] for q in ctx.captured_queries if 'FROM "vositalar_taqsimot"' in q["sql"]]

    assert any("FOR UPDATE" in s for s in sorovlar)


# --- Kutilayotgan 1C chiqimi (spec §6.5): taqsimot = max(1C, 0) + K ---


def chiqim(av, filial, soni, holat="kutilmoqda"):
    from chiqimlar.models import ChiqimHujjat

    return ChiqimHujjat.objects.create(
        hujjat_turi="РеализацияТоваровУслуг", hujjat_raqami="7", hujjat_ref=uuid.uuid4(),
        sana=timezone.now(), av=av, filial=filial, soni=SON(soni), summa=SON("100"),
        holat=holat, taxmin_tur="sotildi",
    )


def _prixodxona_ofis(av, filial):
    """1C 6 -> 4: taqsimlanmagan (prixodxona) 4 + Ofis 2."""
    ofis = qator(av, filial, "2", bolim=Bolim.objects.create(filial=filial, nomi="Ofis"))
    qator(av, filial, "4")
    qoldiq(av, filial, "4")
    AVKartochka.objects.create(av=av)
    return ofis


def test_kutilayotgan_chiqim_taqsimotni_saqlaydi(av, filial_a):
    ofis = _prixodxona_ofis(av, filial_a)
    chiqim(av, filial_a, "2")

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a).soni == SON("4")
    ofis.refresh_from_db()
    assert ofis.soni == SON("2")
    assert stat["mos_emas"] == 0 and stat["kamaydi"] == 0 and stat["kopaydi"] == 0
    assert not TaqsimotHarakat.objects.exists()
    assert farq(av, filial_a) == 0


def test_kutilayotgan_chiqim_filial_nol(av, filial_a, filial_b):
    qoldiq(av, filial_b, "3")
    qator(av, filial_b, "3")
    qoldiq(av, filial_a, "0")
    ofis = qator(av, filial_a, "1", bolim=Bolim.objects.create(filial=filial_a, nomi="Ofis"))
    chiqim(av, filial_a, "1")

    stat = moslashtir()

    assert Taqsimot.objects.filter(pk=ofis.pk, soni=SON("1")).exists()
    assert stat["nolga_tushdi"] == 0 and stat["mos_emas"] == 0
    assert not TaqsimotHarakat.objects.exists()


def test_kutilayotgan_chiqim_qoldiq_qatori_yoq(av, filial_a):
    """1C'da filial qoldig'i qatori umuman yo'q (q=0), K=1 — qator saqlanadi."""
    ofis = qator(av, filial_a, "1", bolim=Bolim.objects.create(filial=filial_a, nomi="Ofis"))
    chiqim(av, filial_a, "1")

    stat = moslashtir()

    assert Taqsimot.objects.filter(pk=ofis.pk).exists()
    assert stat["nolga_tushdi"] == 0 and stat["mos_emas"] == 0


def test_chiqimsiz_kamayish_eskicha(av, filial_a, filial_b):
    ofis = _prixodxona_ofis(av, filial_a)
    chiqim(av, filial_b, "2")  # boshqa juftdagi chiqim bu juftga ta'sir qilmaydi
    qoldiq(av, filial_b, "2")
    qator(av, filial_b, "4")  # filial_b: 2 + K 2 = 4 — mos

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a).soni == SON("2")
    ofis.refresh_from_db()
    assert ofis.soni == SON("2")
    assert stat["kamaydi"] == 1 and stat["mos_emas"] == 0
    assert farq(av, filial_a) == 0


def test_bekor_chiqimdan_keyin_eskicha(av, filial_a):
    _prixodxona_ofis(av, filial_a)
    chiqim(av, filial_a, "2", holat="bekor")
    chiqim(av, filial_a, "2", holat="tasdiqlangan")

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a).soni == SON("2")
    assert stat["kamaydi"] == 1 and stat["mos_emas"] == 0


def test_kutilayotgan_chiqim_kam_taqsimotni_toldiradi(av, filial_a):
    """Σ taqsimot < 1C + K — farq taqsimlanmaganga qo'shiladi (invariant q + K)."""
    qoldiq(av, filial_a, "4")
    qator(av, filial_a, "4")
    chiqim(av, filial_a, "2")

    stat = moslashtir()

    assert taqsimlanmagan(av, filial_a).soni == SON("6")
    assert stat["kopaydi"] == 1 and stat["mos_emas"] == 0


def test_kutilayotgan_chiqim_ortiqcha_mos_emas(av, filial_a):
    qoldiq(av, filial_a, "4")
    qator(av, filial_a, "7", bolim=Bolim.objects.create(filial=filial_a, nomi="Ofis"))
    chiqim(av, filial_a, "2")

    stat = moslashtir()

    assert stat["mos_emas"] == 1
    assert farq(av, filial_a) == SON("-1")


def test_invariant_K_bilan_tekshiriladi(av, filial_a, monkeypatch):
    """Ish K'siz hisoblansa ham invariant K bilan tekshiriladi: kam taqsimot — MoslashXato."""
    from vositalar import moslash

    qoldiq(av, filial_a, "4")
    qator(av, filial_a, "4")
    chiqim(av, filial_a, "2")
    monkeypatch.setattr(moslash, "_kopaydi", lambda *a, **k: None)

    with pytest.raises(MoslashXato):
        moslashtir()


def test_kamaytir_kutilayotgan_chiqimni_ortiqcha_demaydi(av, filial_a, django_user_model):
    from vositalar.amallar import AmalXato, kamaytir

    user = django_user_model.objects.create_user(username="h", password="x")
    qoldiq(av, filial_a, "4")
    q = qator(av, filial_a, "7", bolim=Bolim.objects.create(filial=filial_a, nomi="Ofis"))
    chiqim(av, filial_a, "2")  # ortiqcha faqat 1 (7 - (4 + 2))

    with pytest.raises(AmalXato):
        kamaytir(q, SON("2"), user)
    kamaytir(q, SON("1"), user)

    q.refresh_from_db()
    assert q.soni == SON("6")
    assert farq(av, filial_a) == 0
    with pytest.raises(AmalXato):
        kamaytir(q, SON("1"), user)


def test_kutilayotgan_filtr(av, filial_a, filial_b):
    from django.db.models import Q

    from chiqimlar.servis import kutilayotgan

    chiqim(av, filial_a, "1")
    chiqim(av, filial_a, "2")
    chiqim(av, filial_b, "1.5")
    chiqim(av, filial_b, "5", holat="bekor")

    assert kutilayotgan() == {(av.pk, filial_a.pk): SON("3"), (av.pk, filial_b.pk): SON("1.5")}
    assert kutilayotgan(Q(filial_id__in=[filial_b.pk])) == {(av.pk, filial_b.pk): SON("1.5")}


def test_chiqim_qatorlari_taqsimotdan_oldin_qulflanadi(av, filial_a, monkeypatch):
    """Qulf tartibi ChiqimHujjat -> Taqsimot (Task 4 tasdiqlash bilan bir xil); K qulflangan qatorlardan olinadi."""
    from vositalar import moslash

    _prixodxona_ofis(av, filial_a)
    chiqim(av, filial_a, "2")
    # Ish bosqichida K aggregat so'rovdan emas, qulflangan chiqim qatorlaridan olinishi kerak.
    monkeypatch.setattr(moslash, "_kutilayotgan", lambda filtr=None: {})

    with CaptureQueriesContext(connection) as ctx:
        stat = moslashtir()

    sorovlar = [q["sql"] for q in ctx.captured_queries]
    chiqim_qulf = [i for i, s in enumerate(sorovlar) if 'FROM "chiqimlar_chiqimhujjat"' in s and "FOR UPDATE" in s]
    taqsimot_qulf = [i for i, s in enumerate(sorovlar) if 'FROM "vositalar_taqsimot"' in s and "FOR UPDATE" in s]
    assert chiqim_qulf and taqsimot_qulf
    assert chiqim_qulf[0] < taqsimot_qulf[0]
    assert stat["kamaydi"] == 0  # K=2 qulflangan qatordan: taqsimot saqlandi
    assert taqsimlanmagan(av, filial_a).soni == SON("4")


def test_farq_manfiy_1c_qoldigi_nol_deb_olinadi(av, filial_a):
    from chiqimlar.models import ChiqimHujjat

    qoldiq(av, filial_a, "-3")
    qator(av, filial_a, "2")
    ChiqimHujjat.objects.create(
        hujjat_turi="Реализация", hujjat_raqami="1", hujjat_ref=uuid.uuid4(), sana=timezone.now(), av=av,
        filial=filial_a, soni=SON("2"), summa=SON("1"), taxmin_tur="sotildi",
    )
    assert farq(av, filial_a) == 0  # max(-3, 0) + 2 - 2
