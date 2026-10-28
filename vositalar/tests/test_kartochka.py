import io
import uuid
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from jurnal.models import Jurnal
from jurnal.yoz import yoz
from mol.models import MolAkt, MolAktQator
from onec.models import AVTuri, Harakat1C, Xodim
from vositalar.amallar import AmalXato
from vositalar.models import AVKartochka, AVTuriSozlama, Bolim, Holat, Rasm, Taqsimot, TaqsimotHarakat
from vositalar.qoshimcha import qoshimcha_tekshir
from vositalar.rasmlar import rasm_saqla
from vositalar.tarix import tarix
from vositalar.tests.test_bayroqlar import av_yarat, qator, qoldiq
from vositalar.views import kartochka_saqla

MB = 1024 * 1024


@pytest.fixture(autouse=True)
def vaqtinchalik_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def filial_a(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def filial_b(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def client_hisobchi(client_rol):
    return client_rol("hisobchi")


@pytest.fixture
def cheklangan_client(foydalanuvchi):
    """Fabrika: faqat berilgan filiallarni ko'ra oladigan hisobchi client'i."""

    def yarat(*filiallar):
        client = Client()
        client.force_login(foydalanuvchi("hisobchi", list(filiallar)))
        return client

    return yarat


def rasm_baytlari(eni=100, boyi=80, format="JPEG", exif=None):
    buf = io.BytesIO()
    kw = {"exif": exif} if exif else {}
    Image.new("RGB", (eni, boyi), "red").save(buf, format, **kw)
    return buf.getvalue()


def yuklama(baytlar, nom="r.jpg"):
    return SimpleUploadedFile(nom, baytlar, content_type="image/jpeg")


def kartochka_ol(av):
    return AVKartochka.objects.get_or_create(av=av)[0]


def url(nom, *args):
    return reverse(f"vositalar:{nom}", args=args)


# ---------- kartochka maydonlari ----------

def test_1c_maydonlari_tahrirlanmaydi(client_hisobchi, filial_a):
    av = av_yarat(filial_a, inv="INV-1")
    nomi = av.nomi
    k = kartochka_ol(av)
    javob = client_hisobchi.post(
        url("kartochka", av.pk),
        {"versiya": k.versiya, "nomi": "Buzildi", "inv_raqam": "HACK", "izoh": "yangi izoh"},
    )
    assert javob.status_code in (200, 302)
    av.refresh_from_db()
    k.refresh_from_db()
    assert (av.nomi, av.inv_raqam) == (nomi, "INV-1")
    assert k.izoh == "yangi izoh" and k.versiya == 2
    assert Jurnal.objects.filter(obyekt_turi="vositalar.avkartochka", maydon="izoh").count() == 1


def test_optimistik_blok(client_hisobchi, filial_a, hisobchi):
    av = av_yarat(filial_a)
    k = kartochka_ol(av)
    AVKartochka.objects.filter(pk=k.pk).update(versiya=3, izoh="eski")
    javob = client_hisobchi.post(url("kartochka", av.pk), {"versiya": 1, "izoh": "yangi"})
    assert "Ma&#x27;lumot boshqa foydalanuvchi tomonidan o&#x27;zgartirildi, sahifani yangilang" in javob.content.decode()
    k.refresh_from_db()
    assert (k.izoh, k.versiya) == ("eski", 3)
    with pytest.raises(AmalXato, match="sahifani yangilang"):
        kartochka_saqla(k, {"izoh": "x"}, 1, hisobchi)


def test_kartochka_saqla_faqat_ozgargan_maydon_jurnali(filial_a, hisobchi):
    av = av_yarat(filial_a)
    k = kartochka_ol(av)
    kartochka_saqla(k, {"izoh": "a", "xizmat_muddati_oy": "36", "ishga_tushgan_sana": "2026-01-05"}, 1, hisobchi)
    k.refresh_from_db()
    assert (k.izoh, k.xizmat_muddati_oy, k.ishga_tushgan_sana, k.versiya) == ("a", 36, date(2026, 1, 5), 2)
    maydonlar = set(Jurnal.objects.filter(obyekt_turi="vositalar.avkartochka").values_list("maydon", flat=True))
    assert maydonlar == {"izoh", "xizmat_muddati_oy", "ishga_tushgan_sana"}
    Jurnal.objects.all().delete()
    kartochka_saqla(k, {"izoh": "a", "xizmat_muddati_oy": "36"}, 2, hisobchi)  # o'zgarmadi
    assert not Jurnal.objects.exists()


def test_kartochka_qoshimcha_maydon_saqlanadi(client_hisobchi, filial_a):
    turi = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="Kompyuter")
    AVTuriSozlama.objects.create(
        av_turi=turi, maydonlar=[{"kalit": "seriya", "nomi": "Seriya", "tip": "matn", "majburiy": True}]
    )
    av = av_yarat(filial_a)
    av.turi = turi
    av.save()
    k = kartochka_ol(av)
    bosh = client_hisobchi.post(url("kartochka", av.pk), {"versiya": 1, "q_seriya": ""})
    assert bosh.status_code == 400 and "Seriya" in bosh.content.decode()
    client_hisobchi.post(url("kartochka", av.pk), {"versiya": 1, "q_seriya": "SN-7"})
    k.refresh_from_db()
    assert k.qoshimcha == {"seriya": "SN-7"}
    assert Jurnal.objects.filter(maydon="qoshimcha.seriya", yangi="SN-7").exists()


def test_qoshimcha_tip_va_majburiy():
    maydonlar = [
        {"kalit": "quvvat", "nomi": "Quvvat", "tip": "son"},
        {"kalit": "seriya", "nomi": "Seriya", "tip": "matn", "majburiy": True},
        {"kalit": "rang", "nomi": "Rang", "tip": "tanlov", "tanlov_qiymatlari": ["qizil", "yashil"]},
        {"kalit": "sotib", "nomi": "Sotib olingan", "tip": "sana"},
    ]
    with pytest.raises(ValidationError) as xato:
        qoshimcha_tekshir(maydonlar, {"quvvat": "abc", "seriya": "  ", "rang": "ko'k", "sotib": "32.13.2020"})
    assert set(xato.value.message_dict) == {"quvvat", "seriya", "rang", "sotib"}
    toza = qoshimcha_tekshir(
        maydonlar, {"quvvat": "12,5", "seriya": " AB ", "rang": "qizil", "sotib": "2026-02-03", "begona": "x"}
    )
    assert toza == {"quvvat": "12.5", "seriya": "AB", "rang": "qizil", "sotib": "2026-02-03"}
    assert qoshimcha_tekshir(maydonlar[:1] + maydonlar[2:], {}) == {}


def test_hr_kartochkani_tahrirlolmaydi(client_rol, filial_a):
    av = av_yarat(filial_a)
    k = kartochka_ol(av)
    client = client_rol("hr")
    assert client.get(url("kartochka", av.pk)).status_code == 200
    assert client.post(url("kartochka", av.pk), {"versiya": 1, "izoh": "x"}).status_code == 403
    assert client.post(url("rasm_yukla", av.pk), {"fayl": yuklama(rasm_baytlari())}).status_code == 403
    k.refresh_from_db()
    assert k.izoh == "" and k.versiya == 1


def test_kartochka_filial_cheklovi_404(cheklangan_client, filial_a, filial_b):
    boshqa = av_yarat(filial_b)
    client = cheklangan_client(filial_a)
    assert client.get(url("kartochka", boshqa.pk)).status_code == 404
    assert client.post(url("kartochka", boshqa.pk), {"versiya": 1}).status_code == 404
    assert client.post(url("rasm_yukla", boshqa.pk), {"fayl": yuklama(rasm_baytlari())}).status_code == 404


def test_arxiv_av_kartochkasi_korinadi(client_hisobchi, cheklangan_client, filial_a, filial_b):
    arxiv = av_yarat(filial_a, soni="0")
    assert client_hisobchi.get(url("kartochka", arxiv.pk)).status_code == 200
    assert cheklangan_client(filial_b).get(url("kartochka", arxiv.pk)).status_code == 404


def test_kartochka_sahifasi_qiymatlar(client_hisobchi, filial_a):
    av = av_yarat(filial_a, soni="2")
    k = kartochka_ol(av)
    AVKartochka.objects.filter(pk=k.pk).update(ishga_tushgan_sana=date(2025, 1, 1), xizmat_muddati_oy=60)
    javob = client_hisobchi.get(url("kartochka", av.pk))
    assert javob.status_code == 200
    assert javob.context["amortizatsiya"] is not None
    assert javob.context["dona_narxi"] == Decimal("50")


# ---------- taqsimot ----------

def test_taqsimot_jadvali_jami_belgisi(client_hisobchi, filial_a):
    mos = av_yarat(filial_a, soni="3")
    qator(mos, filial_a, "3")
    html = client_hisobchi.get(url("kartochka", mos.pk)).content.decode()
    assert "1C bilan mos" in html and "Farq:" not in html and "mos emas" not in html

    mos_emas = av_yarat(filial_a, soni="3")
    qator(mos_emas, filial_a, "2")
    javob = client_hisobchi.get(url("kartochka", mos_emas.pk))
    html = javob.content.decode()
    assert "Farq:" in html and "mos emas" in html and "1C bilan mos" not in html
    assert javob.context["taqsimot_guruhlari"][0]["farq"] == Decimal("1")


def test_taqsimot_amal_htmx(client_hisobchi, filial_a):
    av = av_yarat(filial_a, soni="3")
    t = qator(av, filial_a, "3")
    ombor = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    javob = client_hisobchi.post(
        url("taqsimot_amal", av.pk),
        {"amal": "kochir", "qator": t.pk, "soni": "1", "bolim": ombor.pk},
        HTTP_HX_REQUEST="true",
    )
    assert javob.status_code == 200
    nomlar = [x.name for x in javob.templates]
    assert "vositalar/_taqsimot.html" in nomlar and "vositalar/kartochka.html" not in nomlar
    assert Taqsimot.objects.get(av=av, bolim=ombor).soni == Decimal("1")
    assert Taqsimot.objects.get(pk=t.pk).soni == Decimal("2")


def test_taqsimot_amal_holat_va_kamaytir(client_hisobchi, filial_a):
    av = av_yarat(filial_a, soni="2")
    t = qator(av, filial_a, "3")  # 1 ta ortiqcha
    javob = client_hisobchi.post(
        url("taqsimot_amal", av.pk), {"amal": "holat", "qator": t.pk, "soni": "1", "holat": Holat.NOSOZ}
    )
    assert javob.status_code == 200
    assert Taqsimot.objects.get(av=av, holat=Holat.NOSOZ).soni == 1
    javob = client_hisobchi.post(url("taqsimot_amal", av.pk), {"amal": "kamaytir", "qator": t.pk, "soni": "1"})
    assert javob.status_code == 200
    assert Taqsimot.objects.get(pk=t.pk).soni == Decimal("1")
    assert TaqsimotHarakat.objects.filter(sabab="1c_kamaydi").count() == 1


def test_taqsimot_amal_xato_xabari_500_emas(client_hisobchi, filial_a, filial_b):
    av = av_yarat(filial_a, soni="1")
    t = qator(av, filial_a, "1")
    begona_bolim = Bolim.objects.create(filial=filial_b, nomi="Boshqa")
    javob = client_hisobchi.post(
        url("taqsimot_amal", av.pk), {"amal": "kochir", "qator": t.pk, "soni": "1", "bolim": begona_bolim.pk}
    )
    assert javob.status_code == 400 and "Bo&#x27;lim boshqa filialga tegishli" in javob.content.decode()
    javob = client_hisobchi.post(url("taqsimot_amal", av.pk), {"amal": "kochir", "qator": t.pk, "soni": "abc"})
    assert javob.status_code == 400
    javob = client_hisobchi.post(url("taqsimot_amal", av.pk), {"amal": "mol", "qator": t.pk})
    assert javob.status_code == 400  # МОL bu yerda o'zgarmaydi
    assert client_hisobchi.post(url("taqsimot_amal", av.pk), {"amal": "kochir", "qator": "x"}).status_code == 404


def test_taqsimot_amal_ruxsat_va_filial(client_rol, cheklangan_client, filial_a, filial_b):
    av = av_yarat(filial_b)
    t = qator(av, filial_b)
    assert client_rol("hr").post(url("taqsimot_amal", av.pk), {"qator": t.pk}).status_code == 403
    client = cheklangan_client(filial_a)
    assert client.post(url("taqsimot_amal", av.pk), {"amal": "holat", "qator": t.pk}).status_code == 404
    # AV ko'rinadi, lekin qator boshqa AV'niki
    boshqa_av = av_yarat(filial_a)
    assert client.post(url("taqsimot_amal", boshqa_av.pk), {"amal": "holat", "qator": t.pk}).status_code == 404


# ---------- rasmlar ----------

def test_rasm_formati_va_hajmi(filial_a, hisobchi):
    av = av_yarat(filial_a)
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    with pytest.raises(ValidationError):
        rasm_saqla(av, yuklama(gif.getvalue(), "r.jpg"), hisobchi)  # kengaytma jpg, aslida gif
    with pytest.raises(ValidationError):
        rasm_saqla(av, yuklama(b"bu rasm emas"), hisobchi)
    with pytest.raises(ValidationError):
        rasm_saqla(av, yuklama(b"\xff\xd8\xff" + b"0" * (16 * MB)), hisobchi)
    assert not Rasm.objects.exists()

    rasm = rasm_saqla(av, yuklama(rasm_baytlari(4000, 3000)), hisobchi)
    with Image.open(rasm.fayl.path) as asl, Image.open(rasm.miniatyura.path) as mini:
        assert asl.size == (1600, 1200)
        assert max(mini.size) == 300
    assert rasm.asosiy and rasm.kim == hisobchi


def test_birinchi_rasm_asosiy_va_almashtirish(client_hisobchi, filial_a, hisobchi):
    av = av_yarat(filial_a)
    bir = rasm_saqla(av, yuklama(rasm_baytlari()), hisobchi)
    ikki = rasm_saqla(av, yuklama(rasm_baytlari(), "b.jpg"), hisobchi)
    assert bir.asosiy and not ikki.asosiy
    javob = client_hisobchi.post(url("rasm_asosiy", av.pk), {"rasm": ikki.pk}, HTTP_HX_REQUEST="true")
    assert javob.status_code == 200 and "vositalar/_rasmlar.html" in [x.name for x in javob.templates]
    bir.refresh_from_db()
    ikki.refresh_from_db()
    assert (bir.asosiy, ikki.asosiy) == (False, True)
    boshqa_av = av_yarat(filial_a)
    assert client_hisobchi.post(url("rasm_asosiy", boshqa_av.pk), {"rasm": bir.pk}).status_code == 404


def test_rasm_yukla_view_va_xato(client_hisobchi, filial_a):
    av = av_yarat(filial_a)
    javob = client_hisobchi.post(url("rasm_yukla", av.pk), {"fayl": yuklama(rasm_baytlari())}, HTTP_HX_REQUEST="true")
    assert javob.status_code == 200 and Rasm.objects.filter(av=av, asosiy=True).count() == 1
    rad = client_hisobchi.post(url("rasm_yukla", av.pk), {"fayl": yuklama(b"xxx")}, HTTP_HX_REQUEST="true")
    assert rad.status_code == 400 and Rasm.objects.count() == 1
    assert client_hisobchi.post(url("rasm_yukla", av.pk), {}).status_code == 400


def test_rasm_exif_yonalishi(filial_a, hisobchi):
    exif = Image.Exif()
    exif[0x0112] = 6  # 90 gradus soat strelkasi bo'yicha
    rasm = rasm_saqla(av_yarat(filial_a), yuklama(rasm_baytlari(400, 200, exif=exif.tobytes())), hisobchi)
    with Image.open(rasm.fayl.path) as im:
        assert im.size == (200, 400)


def test_rasm_fayl_filial_cheklovi(cheklangan_client, filial_a, filial_b, hisobchi):
    boshqa = av_yarat(filial_b)
    rasm = rasm_saqla(boshqa, yuklama(rasm_baytlari()), hisobchi)
    oz = av_yarat(filial_a)
    oz_rasm = rasm_saqla(oz, yuklama(rasm_baytlari()), hisobchi)
    client = cheklangan_client(filial_a)
    assert client.get(url("rasm_fayl", rasm.pk)).status_code == 404
    assert client.get(url("rasm_fayl", rasm.pk) + "?mini=1").status_code == 404
    javob = client.get(url("rasm_fayl", oz_rasm.pk))
    assert javob.status_code == 200 and b"".join(javob.streaming_content).startswith(b"\xff\xd8")
    assert client.get(url("rasm_fayl", oz_rasm.pk) + "?mini=1").status_code == 200
    assert Client().get(url("rasm_fayl", oz_rasm.pk)).status_code == 302  # kirmagan -> kirish
    assert client.get(url("rasm_fayl", 999999)).status_code == 404


# ---------- tarix ----------

def test_tarix_tartibi(filial_a, hisobchi):
    av = av_yarat(filial_a, soni="2")
    k = kartochka_ol(av)
    ali = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Ali")
    t = qator(av, filial_a, "2")

    def utc(*a):
        return datetime(*a, tzinfo=dt_timezone.utc)

    Harakat1C.objects.create(
        sana=utc(2026, 1, 10, 8), hujjat_turi="Kirim", hujjat_raqami="5", hujjat_ref=uuid.uuid4(), av=av,
        filial=filial_a, vid="kirim", soni=Decimal("2"), summa=Decimal("100"),
    )
    TaqsimotHarakat.objects.create(
        av=av, filial=filial_a, yangi_holat=Holat.NOSOZ, eski_holat=Holat.ISHLATILMOQDA, soni=Decimal("1"),
        sana=utc(2026, 3, 1, 10), kim=hisobchi, sabab="holat",
    )
    akt = MolAkt.objects.create(raqam=1, sana=date(2026, 2, 1), qabul_qiluvchi=ali, tuzdi=hisobchi)
    MolAktQator.objects.create(akt=akt, av=av, filial=filial_a, holat=Holat.ISHLATILMOQDA, soni=Decimal("1"))
    MolAkt.objects.create(raqam=2, sana=date(2026, 2, 2), qabul_qiluvchi=ali, tuzdi=hisobchi)  # boshqa AV
    Rasm.objects.create(av=av, fayl="rasmlar/x.jpg", qachon=utc(2026, 4, 1), kim=hisobchi)
    yoz(hisobchi, k, "izoh", "", "x")
    Jurnal.objects.filter(maydon="izoh").update(qachon=utc(2026, 5, 1))
    yoz(hisobchi, t, "soni", 2, 1)  # Taqsimot jurnali tarixga kirmaydi (TaqsimotHarakat bilan takror)

    qatorlar = tarix(av, hisobchi)
    assert [q.tur for q in qatorlar] == ["jurnal", "rasm", "holat", "mol_akt", "1c"]
    assert [q.sana for q in qatorlar] == sorted((q.sana for q in qatorlar), reverse=True)
    assert all(q.sana.tzinfo is not None for q in qatorlar)
    assert qatorlar[0].kim and "Izoh" in qatorlar[0].matn
    assert "MA-000001" in qatorlar[3].matn


def test_tarix_sahifada(client_hisobchi, filial_a):
    av = av_yarat(filial_a)
    kartochka_ol(av)
    Rasm.objects.create(av=av, fayl="rasmlar/x.jpg")
    assert "Rasm yuklandi" in client_hisobchi.get(url("kartochka", av.pk)).content.decode()


def test_kartochka_sahifasi_sorovlar_soni_o_smaydi(client_hisobchi, filial_a, hisobchi, django_assert_max_num_queries):
    av = av_yarat(filial_a, soni="3")
    kartochka_ol(av)
    for i in range(6):
        qator(av, filial_a, "0.5", bolim=Bolim.objects.create(filial=filial_a, nomi=f"B{i}"))
        rasm_saqla(av, yuklama(rasm_baytlari()), hisobchi)
        TaqsimotHarakat.objects.create(
            av=av, filial=filial_a, yangi_holat=Holat.NOSOZ, soni=Decimal("1"), kim=hisobchi, sabab="holat"
        )
    with django_assert_max_num_queries(33):  # +2: reviziya qaydlari; +1: ko'rinadigan filiallar qoldig'i
        assert client_hisobchi.get(url("kartochka", av.pk)).status_code == 200


def test_mpo_rasm_jpeg_sifatida_saqlanadi(filial_a, hisobchi):
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "red").save(
        buf, "MPO", save_all=True, append_images=[Image.new("RGB", (300, 200), "blue")]
    )
    with Image.open(io.BytesIO(buf.getvalue())) as tekshir:
        assert tekshir.format == "MPO"
    rasm = rasm_saqla(av_yarat(filial_a), yuklama(buf.getvalue()), hisobchi)
    assert rasm.fayl.name.endswith(".jpg")
    with Image.open(rasm.fayl.path) as im:
        assert im.format == "JPEG"


def test_htmx_4xx_javoblarni_almashtirish_sozlamasi(client_hisobchi):
    html = client_hisobchi.get(reverse("panel:bosh"), follow=True).content.decode()
    assert 'name="htmx-config"' in html and "responseHandling" in html
    assert "400|409|422" in html


def test_tarix_boshqa_filialni_oshkor_qilmaydi(foydalanuvchi, filial_a, filial_b, hisobchi):
    """Ikki filialda qoldig'i bor AV: faqat A'ga ruxsatli foydalanuvchi B'ning bo'lim/xodim nomlari, 1C summalari
    va aktlarini tarixda ko'rmaydi."""
    av = av_yarat(filial_a, soni="1")
    qoldiq(av, filial_b, "1")
    kartochka_ol(av)
    user_a = foydalanuvchi("hisobchi", [filial_a])
    b_bolim = Bolim.objects.create(filial=filial_b, nomi="Bbolimi")
    b_xodim = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Bxodimi", filial=filial_b)
    a_xodim = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Axodimi", filial=filial_a)
    for filial, summa in ((filial_a, "111"), (filial_b, "98765")):
        Harakat1C.objects.create(
            sana=datetime(2026, 1, 10, 8, tzinfo=dt_timezone.utc), hujjat_turi="Kirim", hujjat_raqami="5",
            hujjat_ref=uuid.uuid4(), av=av, filial=filial, vid="kirim", soni=Decimal("1"), summa=Decimal(summa),
        )
    TaqsimotHarakat.objects.create(
        av=av, filial=filial_b, yangi_bolim=b_bolim, yangi_mol=b_xodim, yangi_holat=Holat.ISHLATILMOQDA,
        soni=Decimal("1"), kim=hisobchi, sabab="kochirish",
    )
    TaqsimotHarakat.objects.create(
        av=av, filial=filial_a, yangi_mol=a_xodim, yangi_holat=Holat.ISHLATILMOQDA, soni=Decimal("1"),
        kim=hisobchi, sabab="kochirish",
    )
    akt_b = MolAkt.objects.create(raqam=7, qabul_qiluvchi=b_xodim, tuzdi=hisobchi)
    MolAktQator.objects.create(akt=akt_b, av=av, filial=filial_b, holat=Holat.ISHLATILMOQDA, soni=Decimal("1"))
    akt_a = MolAkt.objects.create(raqam=8, qabul_qiluvchi=a_xodim, tuzdi=hisobchi)
    MolAktQator.objects.create(akt=akt_a, av=av, filial=filial_a, holat=Holat.ISHLATILMOQDA, soni=Decimal("1"))

    matn = " ".join(f"{q.matn} {q.summa}" for q in tarix(av, user_a))
    for begona in ("Bbolimi", "Bxodimi", "98765", "MA-000007", "Filial B"):
        assert begona not in matn
    for oziniki in ("Axodimi", "111", "MA-000008"):
        assert oziniki in matn
    html = client_user(user_a).get(url("kartochka", av.pk)).content.decode()
    assert "Bxodimi" not in html and "98765" not in html and "MA-000007" not in html
    hammasi = " ".join(f"{q.matn} {q.summa}" for q in tarix(av, foydalanuvchi("admin")))
    assert "Bxodimi" in hammasi and "98765" in hammasi and "MA-000007" in hammasi


def client_user(user):
    c = Client()
    c.force_login(user)
    return c


def test_molsiz_qatorda_mol_biriktirish_havolasi(client_rol, filial_a):
    from onec.models import Xodim
    import uuid as _uuid
    av = av_yarat(filial_a, soni="5")
    molsiz = qator(av, filial_a, "3")
    xodim = Xodim.objects.create(ref_1c=_uuid.uuid4(), ism="Aziz", filial=filial_a)
    molli = qator(av, filial_a, "2", mol=xodim)
    asos = reverse("mol:akt_yangi")
    for rol in ("hisobchi", "hr"):
        html = client_rol(rol).get(url("kartochka", av.pk)).content.decode()
        assert f'href="{asos}?qator={molsiz.pk}"' in html
        assert f"?qator={molli.pk}" not in html
    assert asos not in client_rol("rahbar").get(url("kartochka", av.pk)).content.decode()


def test_tarixda_reviziya_qaydi(filial_a, filial_b, foydalanuvchi):
    from reviziya.models import Reviziya, ReviziyaQayd

    av = av_yarat(filial_a, "RV1")
    hisobchi = foydalanuvchi("hisobchi")
    rv = Reviziya.objects.create(raqam=1, filial=filial_a, ochdi=hisobchi)
    xona = Bolim.objects.create(filial=filial_a, nomi="Xona 5")
    ReviziyaQayd.objects.create(
        reviziya=rv, bolim=xona, av=av, soni=Decimal("2"), holat=Holat.ISHLATILMOQDA, usul="qidiruv", kim=hisobchi
    )
    qatorlar = [q for q in tarix(av, hisobchi) if q.tur == "reviziya"]
    assert len(qatorlar) == 1
    assert "RV-000001" in qatorlar[0].matn and "Xona 5da topildi" in qatorlar[0].matn
    assert Holat.ISHLATILMOQDA.label in qatorlar[0].matn
    boshqa = foydalanuvchi("hisobchi", [filial_b])
    assert not [q for q in tarix(av, boshqa) if q.tur == "reviziya"]


def test_tarixda_bekor_reviziya_qaydi_yoq(filial_a, foydalanuvchi):
    from reviziya.models import Reviziya, ReviziyaQayd

    av = av_yarat(filial_a, "RV2")
    hisobchi = foydalanuvchi("hisobchi")
    bekor = Reviziya.objects.create(raqam=1, filial=filial_a, ochdi=hisobchi, holat=Reviziya.Holat.BEKOR)
    ochiq = Reviziya.objects.create(raqam=2, filial=filial_a, ochdi=hisobchi)
    for rv in (bekor, ochiq):
        ReviziyaQayd.objects.create(
            reviziya=rv, av=av, soni=Decimal("1"), holat=Holat.ISHLATILMOQDA, usul="qidiruv", kim=hisobchi
        )
    qatorlar = [q for q in tarix(av, hisobchi) if q.tur == "reviziya"]
    assert len(qatorlar) == 1 and "RV-000002" in qatorlar[0].matn
