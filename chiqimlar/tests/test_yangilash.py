import uuid
from datetime import datetime, timedelta, timezone as dt_tz
from decimal import Decimal

import pytest

from chiqimlar.models import ChiqimHujjat
from chiqimlar.servis import TAXMIN_OYNASI, chiqimlarni_yangila, taxmin_qil
from jurnal.models import Jurnal
from onec.models import AV, Harakat1C
from vositalar.models import Sozlama

pytestmark = pytest.mark.django_db

BOSH = datetime(2026, 9, 1, tzinfo=dt_tz.utc)
DAN = datetime(2026, 8, 1, tzinfo=dt_tz.utc)
GACHA = datetime(2026, 12, 31, tzinfo=dt_tz.utc)
SANA = datetime(2026, 9, 10, 12, 0, tzinfo=dt_tz.utc)


@pytest.fixture(autouse=True)
def boshlanish():
    Sozlama.objects.update_or_create(pk=1, defaults={"chiqim_boshlanishi": BOSH})


@pytest.fixture
def av():
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def fb(filial_yarat):
    return filial_yarat("B")


def harakat(av, filial, vid, sana, soni, turi="Реализация", ref=None, summa=100):
    return Harakat1C.objects.create(
        sana=sana, hujjat_turi=turi, hujjat_raqami="7", hujjat_ref=ref or uuid.uuid4(),
        av=av, filial=filial, vid=vid, soni=soni, summa=summa,
    )


def yangila():
    return chiqimlarni_yangila(DAN, GACHA)


def test_boshlanishdan_oldingi_chiqim_yaratilmaydi(av, fa):
    harakat(av, fa, "chiqim", BOSH - timedelta(days=1), 1)
    assert yangila()["yaratildi"] == 0
    assert ChiqimHujjat.objects.count() == 0


def test_yangi_chiqim_kutilmoqda(av, fa):
    ref = uuid.uuid4()
    harakat(av, fa, "chiqim", SANA, 2, ref=ref, summa=250)
    assert yangila() == {"yaratildi": 1, "yangilandi": 0, "bekor": 0, "qaytdi": 0}
    c = ChiqimHujjat.objects.get()
    assert (c.holat, c.soni, c.summa, c.sana) == ("kutilmoqda", Decimal(2), Decimal(250), SANA)
    assert (c.hujjat_ref, c.hujjat_turi, c.hujjat_raqami, c.av, c.filial) == (ref, "Реализация", "7", av, fa)
    assert c.taxmin_tur == "sotildi"


def test_bir_hujjatda_ikki_qator_yigiladi(av, fa):
    ref = uuid.uuid4()
    harakat(av, fa, "chiqim", SANA, 2, ref=ref, summa=100)
    harakat(av, fa, "chiqim", SANA + timedelta(minutes=1), 3, ref=ref, summa=50)
    yangila()
    c = ChiqimHujjat.objects.get()
    assert (c.soni, c.summa, c.sana) == (Decimal(5), Decimal(150), SANA)


def test_soni_nol_va_kirim_yaratilmaydi(av, fa):
    harakat(av, fa, "chiqim", SANA, 0)
    harakat(av, fa, "kirim", SANA, 1)
    assert yangila()["yaratildi"] == 0
    assert ChiqimHujjat.objects.count() == 0


def test_takroriy_chaqiriq_idempotent(av, fa):
    harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    assert yangila() == {"yaratildi": 0, "yangilandi": 0, "bekor": 0, "qaytdi": 0}
    assert ChiqimHujjat.objects.count() == 1


def test_1c_da_soni_ozgarsa_yangilanadi(av, fa):
    h = harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    h.soni = 4
    h.save()
    assert yangila()["yangilandi"] == 1
    assert ChiqimHujjat.objects.get().soni == Decimal(4)


def test_tasdiqlangan_ozgarmaydi(av, fa):
    h = harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    ChiqimHujjat.objects.update(holat="tasdiqlangan")
    h.soni = 4
    h.save()
    assert yangila() == {"yaratildi": 0, "yangilandi": 0, "bekor": 0, "qaytdi": 0}
    c = ChiqimHujjat.objects.get()
    assert (c.holat, c.soni) == ("tasdiqlangan", Decimal(1))


def test_oraliqda_yoqolsa_bekor(av, fa):
    harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    Harakat1C.objects.all().delete()
    assert yangila()["bekor"] == 1
    c = ChiqimHujjat.objects.get()
    assert c.holat == "bekor"
    j = Jurnal.objects.get(obyekt_turi="chiqimlar.chiqimhujjat", obyekt_id=str(c.pk))
    assert (j.maydon, j.eski, j.yangi, j.kim_nomi) == ("holat", "kutilmoqda", "bekor", "1C sinxron")


def test_oraliqdan_tashqarisi_bekor_qilinmaydi(av, fa):
    harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    Harakat1C.objects.all().delete()
    # Sinxron oynasi chiqim sanasidan keyin boshlanadi: harakat yo'qligi bekor degani emas.
    stat = chiqimlarni_yangila(SANA + timedelta(days=1), GACHA)
    assert stat["bekor"] == 0
    assert ChiqimHujjat.objects.get().holat == "kutilmoqda"


def test_taxmin_otkazish(av, fa, fb):
    harakat(av, fb, "kirim", SANA + timedelta(days=2), 1)
    assert taxmin_qil(av.pk, fa.pk, SANA, "Реализация") == ("otkazish", fb.pk)


def test_taxmin_sotildi_4_kundan_keyin(av, fa, fb):
    assert TAXMIN_OYNASI == timedelta(days=3)
    harakat(av, fb, "kirim", SANA + timedelta(days=4), 1)
    assert taxmin_qil(av.pk, fa.pk, SANA, "Реализация") == ("sotildi", None)


def test_taxmin_spisanie(av, fa, fb):
    harakat(av, fb, "kirim", SANA + timedelta(days=1), 1)
    assert taxmin_qil(av.pk, fa.pk, SANA, "СписаниеОС") == ("hisobdan_chiqarildi", None)


def test_taxmin_kirim_oldin_2_kun_otkazish(av, fa, fb):
    harakat(av, fb, "kirim", SANA - timedelta(days=2), 1)
    assert taxmin_qil(av.pk, fa.pk, SANA, "Реализация") == ("otkazish", fb.pk)


def test_taxmin_kirim_oldin_4_kun_sotildi(av, fa, fb):
    harakat(av, fb, "kirim", SANA - timedelta(days=4), 1)
    assert taxmin_qil(av.pk, fa.pk, SANA, "Реализация") == ("sotildi", None)


def test_taxmin_soni_nol_kirim_sotildi(av, fa, fb):
    harakat(av, fb, "kirim", SANA + timedelta(days=1), 0)
    assert taxmin_qil(av.pk, fa.pk, SANA, "Реализация") == ("sotildi", None)


def test_taxmin_bir_xil_filial_kirimi_sotildi(av, fa):
    harakat(av, fa, "kirim", SANA + timedelta(days=1), 1)
    assert taxmin_qil(av.pk, fa.pk, SANA, "Реализация") == ("sotildi", None)


def test_filial_ozgarsa_eski_bekor_yangi_yaratiladi(av, fa, filial_yarat):
    fc = filial_yarat("C")
    ref = uuid.uuid4()
    h = harakat(av, fa, "chiqim", SANA, 1, ref=ref)
    yangila()
    h.filial = fc
    h.save()
    assert yangila() == {"yaratildi": 1, "yangilandi": 0, "bekor": 1, "qaytdi": 0}
    assert ChiqimHujjat.objects.get(filial=fa).holat == "bekor"
    assert ChiqimHujjat.objects.get(filial=fc).holat == "kutilmoqda"


def test_bekor_chiqim_qayta_paydo_bolsa_kutilmoqda(av, fa):
    """1C hujjati qayta o'tkazildi: `bekor` yozuv `kutilmoqda`ga qaytadi (aks holda K=0 va taqsimot tasdiqsiz o'chadi)."""
    ref = uuid.uuid4()
    harakat(av, fa, "chiqim", SANA, 1, ref=ref)
    yangila()
    Harakat1C.objects.all().delete()
    yangila()
    assert ChiqimHujjat.objects.get().holat == "bekor"
    harakat(av, fa, "chiqim", SANA + timedelta(hours=1), 2, ref=ref, summa=250)

    assert yangila() == {"yaratildi": 0, "yangilandi": 0, "bekor": 0, "qaytdi": 1}
    c = ChiqimHujjat.objects.get()
    assert (c.holat, c.soni, c.summa, c.sana) == ("kutilmoqda", Decimal(2), Decimal(250), SANA + timedelta(hours=1))
    j = Jurnal.objects.filter(obyekt_turi="chiqimlar.chiqimhujjat", obyekt_id=str(c.pk)).order_by("-pk").first()
    assert (j.maydon, j.eski, j.yangi, j.kim_nomi) == ("holat", "bekor", "kutilmoqda", "1C sinxron")
    assert yangila() == {"yaratildi": 0, "yangilandi": 0, "bekor": 0, "qaytdi": 0}


def test_taxmin_keyin_kelgan_kirim_bilan_yangilanadi(av, fa, fb):
    harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    assert ChiqimHujjat.objects.get().taxmin_tur == "sotildi"
    harakat(av, fb, "kirim", SANA + timedelta(days=2), 1, turi="Поступление")
    yangila()
    c = ChiqimHujjat.objects.get()
    assert c.taxmin_tur == "otkazish" and c.holat == "kutilmoqda"
    assert not Jurnal.objects.filter(obyekt_turi="chiqimlar.chiqimhujjat", maydon="taxmin_tur").exists()


def test_taxmin_tasdiqlanganga_tegmaydi(av, fa, fb):
    harakat(av, fa, "chiqim", SANA, 1)
    yangila()
    ChiqimHujjat.objects.update(holat="tasdiqlangan", tur="sotildi")
    harakat(av, fb, "kirim", SANA + timedelta(days=2), 1, turi="Поступление")
    yangila()
    assert ChiqimHujjat.objects.get().taxmin_tur == "sotildi"
