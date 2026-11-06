"""AV turi: qo'shimcha maydonlarni boshqa turlarga nusxalash."""
import uuid

import pytest
from django.urls import reverse

from jurnal.models import Jurnal
from onec.models import AVTuri
from panel.sozlamalar import MAX_MAYDON
from vositalar.models import AVKartochka, AVTuriSozlama
from vositalar.tests.test_bayroqlar import av_yarat

pytestmark = pytest.mark.django_db

CPU = {"kalit": "cpu", "nomi": "Protsessor", "tip": "tanlov", "majburiy": True, "tanlov_qiymatlari": ["i5", "i7"]}
RAM = {"kalit": "ram", "nomi": "Xotira", "tip": "matn", "majburiy": False, "tanlov_qiymatlari": []}


def tur_yarat(nomi, *maydonlar, muddat=None):
    tur = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi=nomi)
    if maydonlar or muddat:
        AVTuriSozlama.objects.create(av_turi=tur, maydonlar=list(maydonlar), xizmat_muddati_oy=muddat)
    return tur


def nusxala(client, manba, *turlar):
    return client.post(reverse("panel:av_turi_nusxa", args=[manba.pk]), {"turlar": [t.pk for t in turlar]}, follow=True)


def maydonlar(tur):
    return AVTuriSozlama.objects.get(av_turi=tur).maydonlar


@pytest.fixture
def admin(client_rol):
    return client_rol("admin")


@pytest.fixture
def manba():
    return tur_yarat("KOMPYUTERLAR", CPU, RAM, muddat=36)


def test_sozlamasiz_turga_maydonlar_qoshiladi(admin, manba):
    a, b = tur_yarat("A"), tur_yarat("B")

    javob = nusxala(admin, manba, a, b)

    assert maydonlar(a) == [CPU, RAM] and maydonlar(b) == [CPU, RAM]
    assert "2 ta turga" in javob.content.decode()


def test_mavjud_maydon_ochmaydi_faqat_yetishmagani_qoshiladi(admin, manba):
    ozgacha = {**CPU, "nomi": "Boshqa nom", "majburiy": False}
    a = tur_yarat("A", ozgacha, {**RAM, "kalit": "rang", "nomi": "Rang"})

    nusxala(admin, manba, a)

    assert [m["kalit"] for m in maydonlar(a)] == ["cpu", "rang", "ram"]
    assert maydonlar(a)[0] == ozgacha


def test_xizmat_muddati_va_manba_ozgarmaydi(admin, manba):
    a = tur_yarat("A", muddat=12)

    nusxala(admin, manba, a)

    assert AVTuriSozlama.objects.get(av_turi=a).xizmat_muddati_oy == 12
    assert maydonlar(manba) == [CPU, RAM]


def test_kartochka_qiymatlari_saqlanadi(admin, manba, filial_yarat):
    a = tur_yarat("A")
    k = AVKartochka.objects.create(av=av_yarat(filial_yarat("01"), turi=a), qoshimcha={"eski": "qiymat"})

    nusxala(admin, manba, a)

    k.refresh_from_db()
    assert k.qoshimcha == {"eski": "qiymat"}


def test_ozgarish_jurnalga_yoziladi(admin, manba):
    sozlama_oldin = Jurnal.objects.count()

    nusxala(admin, manba, tur_yarat("A"))

    assert Jurnal.objects.count() == sozlama_oldin + 1
    assert Jurnal.objects.filter(maydon="maydonlar", yangi__contains="cpu").exists()


def test_hamma_maydoni_bor_turga_jurnal_yozilmaydi(admin, manba):
    a = tur_yarat("A", CPU, RAM)
    oldin = Jurnal.objects.count()

    javob = nusxala(admin, manba, a)

    assert Jurnal.objects.count() == oldin
    assert "Hamma maydon" in javob.content.decode()


def test_tur_tanlanmasa_xato(admin, manba):
    assert "kamida bitta tur" in nusxala(admin, manba).content.decode()


def test_ozini_nusxalab_bolmaydi(admin, manba):
    assert "kamida bitta tur" in nusxala(admin, manba, manba).content.decode()
    assert maydonlar(manba) == [CPU, RAM]


def test_chegaradan_oshsa_tur_ozgarmaydi(admin, manba):
    toliq = [{**RAM, "kalit": f"m{i}"} for i in range(MAX_MAYDON)]
    a = tur_yarat("A", *toliq)

    javob = nusxala(admin, manba, a)

    assert maydonlar(a) == toliq
    assert "sig&#x27;madi" in javob.content.decode()


def test_faqat_sozlama_huquqi_bilan(client_rol, manba):
    a = tur_yarat("A")

    javob = client_rol("hisobchi").post(reverse("panel:av_turi_nusxa", args=[manba.pk]), {"turlar": [a.pk]})

    assert javob.status_code == 403 and not AVTuriSozlama.objects.filter(av_turi=a).exists()


def test_get_qabul_qilinmaydi(admin, manba):
    assert admin.get(reverse("panel:av_turi_nusxa", args=[manba.pk])).status_code == 405


def test_forma_faqat_saqlangan_maydon_bolsa_chiqadi(admin, manba):
    bosh = tur_yarat("Bosh")

    assert "Maydonlarni boshqa turlarga nusxalash" in admin.get(reverse("panel:av_turi_tahrir", args=[manba.pk])).content.decode()
    assert "Maydonlarni boshqa turlarga nusxalash" not in admin.get(reverse("panel:av_turi_tahrir", args=[bosh.pk])).content.decode()


def test_royxatda_av_soni_chiqadi_va_oz_turi_yoq(admin, manba, filial_yarat):
    a = tur_yarat("Bir xil nom")
    av_yarat(filial_yarat("01"), turi=a)

    html = admin.get(reverse("panel:av_turi_tahrir", args=[manba.pk])).content.decode()

    assert "Bir xil nom" in html and "1 ta AV" in html
    assert f'name="turlar" value="{manba.pk}"' not in html
