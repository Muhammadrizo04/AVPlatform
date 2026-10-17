import io
from datetime import date
from decimal import Decimal

import pytest
import zxingcpp
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader

from jurnal.models import Jurnal
from onec.models import AV
from vositalar.bayroqlar import BAYROQLAR
from vositalar.models import AVKartochka, YorliqOlchami
from vositalar.tests.test_bayroqlar import av_yarat
from yorliqlar import servis

MM = 72 / 25.4


@pytest.fixture
def filial_a(filial_yarat):
    return filial_yarat("07", "Toshkent filiali")


@pytest.fixture
def filial_b(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def olcham_40(db):
    return YorliqOlchami.standarti()


def qayta(av):
    return AV.objects.select_related("filial_rekvizit").get(pk=av.pk)


def sahifalar(pdf: bytes):
    return PdfReader(io.BytesIO(pdf)).pages


def test_belgi_soni():
    assert servis.belgi_soni(YorliqOlchami(eni_mm=Decimal("40"), boyi_mm=Decimal("30"))) == 22
    assert servis.belgi_soni(YorliqOlchami(eni_mm=Decimal("58"), boyi_mm=Decimal("40"))) == 31


def test_qr_matni(filial_a):
    av = qayta(av_yarat(filial_a, inv="125"))
    rasm = Image.open(io.BytesIO(servis.qr_png(av.kalit)))
    natija = zxingcpp.read_barcodes(rasm)
    assert [n.text for n in natija] == ["DS|07|125"]


def test_kalitsiz_av_rad(filial_a, olcham_40):
    av = qayta(av_yarat(filial_a, inv=""))
    with pytest.raises(ValueError):
        servis.yorliq_pdf([(av, 1)], olcham_40)


def test_nusxalar_soni(filial_a, olcham_40):
    guruh = qayta(av_yarat(filial_a, inv="G1", soni="20"))
    assert len(sahifalar(servis.yorliq_pdf([(guruh, 20)], olcham_40))) == 20


def test_sahifa_olchami(filial_a, olcham_40):
    av = qayta(av_yarat(filial_a, inv="1"))
    sahifa = sahifalar(servis.yorliq_pdf([(av, 1)], olcham_40))[0]
    assert float(sahifa.mediabox.width) == pytest.approx(113.39, abs=0.5)
    assert float(sahifa.mediabox.height) == pytest.approx(85.04, abs=0.5)
    yangi = YorliqOlchami.objects.create(nomi="50×25", eni_mm=Decimal("50"), boyi_mm=Decimal("25"))
    sahifa = sahifalar(servis.yorliq_pdf([(av, 1)], yangi))[0]
    assert float(sahifa.mediabox.width) == pytest.approx(141.73, abs=0.5)
    assert float(sahifa.mediabox.height) == pytest.approx(70.87, abs=0.5)


def test_qisqa_nom_uzun_nom(olcham_40):
    qatorlar = servis.qisqa_nom("Ab " * 40, olcham_40)
    assert len(qatorlar) == 2
    assert qatorlar[-1].endswith("…")
    assert all(len(q) <= 22 for q in qatorlar)


def test_qisqa_nom_qisqa_va_bosh(olcham_40):
    assert servis.qisqa_nom("Stol", olcham_40) == ["Stol"]
    assert servis.qisqa_nom("  ", olcham_40) == []


def test_chop_etildi_kalitni_yozadi(filial_a, foydalanuvchi, olcham_40):
    user = foydalanuvchi("hisobchi")
    av = qayta(av_yarat(filial_a, inv="125"))
    AVKartochka.objects.create(av=av, yorliq_kaliti="DS|07|OLD")
    assert av.pk in {a.pk for a in BAYROQLAR["yorliq_almashtirish"].so_rov(user, date.today())}
    servis.chop_etildi([av], user)
    kartochka = AVKartochka.objects.get(av=av)
    assert kartochka.yorliq_kaliti == "DS|07|125"
    assert kartochka.yorliq_sana is not None
    assert av.pk not in {a.pk for a in BAYROQLAR["yorliq_almashtirish"].so_rov(user, date.today())}
    assert Jurnal.objects.filter(maydon="yorliq_kaliti", yangi="DS|07|125", eski="DS|07|OLD").count() == 1


def test_standarti_zaxira(db):
    YorliqOlchami.objects.filter(standart=True).update(standart=False, faol=False)
    assert YorliqOlchami.standarti().faol
    YorliqOlchami.objects.update(faol=False)
    with pytest.raises(YorliqOlchami.DoesNotExist, match="o'lcham"):
        YorliqOlchami.standarti()


# ---------- view'lar ----------

PDF = "yorliqlar:pdf"
TANLASH = "yorliqlar:tanlash"


def test_pdf_view_chop_etadi(client_rol, filial_a, olcham_40):
    client = client_rol("hisobchi")
    av = av_yarat(filial_a, inv="125", soni="3")
    javob = client.post(reverse(PDF), {"av": [av.pk], f"nusxa_{av.pk}": "3", "olcham": olcham_40.pk})
    assert javob.status_code == 200
    assert javob["Content-Type"] == "application/pdf"
    assert len(sahifalar(javob.content)) == 3
    assert AVKartochka.objects.get(av=av).yorliq_kaliti == "DS|07|125"


def test_yorliq_pdf_filial_cheklovi(foydalanuvchi, filial_a, filial_b, olcham_40):
    from django.test import Client

    user = foydalanuvchi("hisobchi", [filial_a])
    client = Client()
    client.force_login(user)
    boshqa = av_yarat(filial_b, inv="9")
    javob = client.post(reverse(PDF), {"av": [boshqa.pk], f"nusxa_{boshqa.pk}": "1", "olcham": olcham_40.pk})
    assert javob.status_code == 404
    assert not AVKartochka.objects.filter(av=boshqa).exists()
    assert client.get(reverse(TANLASH), {"av": boshqa.pk}).status_code == 404


def test_nofaol_olcham_tanlanmaydi(client_rol, filial_a):
    client = client_rol("hisobchi")
    nofaol = YorliqOlchami.objects.create(nomi="X", eni_mm=Decimal("50"), boyi_mm=Decimal("30"), faol=False)
    av = av_yarat(filial_a, inv="1")
    for olcham in (nofaol.pk, 999999, "abc"):
        javob = client.post(reverse(PDF), {"av": [av.pk], f"nusxa_{av.pk}": "1", "olcham": olcham})
        assert javob.status_code == 404
    assert not AVKartochka.objects.filter(av=av).exists()


def test_view_kalitsiz_av_xabar(client_rol, filial_a, olcham_40):
    client = client_rol("hisobchi")
    av = av_yarat(filial_a, inv="")
    javob = client.post(reverse(PDF), {"av": [av.pk], f"nusxa_{av.pk}": "1", "olcham": olcham_40.pk}, follow=True)
    assert javob["Content-Type"].startswith("text/html")
    assert "inv. raqam" in " ".join(str(m) for m in javob.context["messages"]).lower()
    assert not AVKartochka.objects.filter(av=av).exists()


def test_nusxa_xato(client_rol, filial_a, olcham_40):
    client = client_rol("hisobchi")
    av = av_yarat(filial_a, inv="1")
    for nusxa in ("0", "-2", "x", "100000"):
        javob = client.post(reverse(PDF), {"av": [av.pk], f"nusxa_{av.pk}": nusxa, "olcham": olcham_40.pk})
        assert javob["Content-Type"].startswith("text/html") or javob.status_code == 302
    assert not AVKartochka.objects.filter(av=av).exists()


def test_tanlash_manbalar(client_rol, filial_a):
    client = client_rol("hisobchi")
    bir = av_yarat(filial_a, inv="1", soni="5")
    ikki = av_yarat(filial_a, inv="2")
    javob = client.get(reverse(TANLASH), {"av": [bir.pk]})
    assert [e["av"].pk for e in javob.context["elementlar"]] == [bir.pk]
    assert javob.context["elementlar"][0]["nusxa"] == 5
    javob = client.get(reverse(TANLASH), {"bayroq": "yorliq_yoq"})
    assert {e["av"].pk for e in javob.context["elementlar"]} == {bir.pk, ikki.pk}
    assert client.get(reverse(TANLASH), {"bayroq": "yo'q"}).context["elementlar"] == []
    assert client.get(reverse(TANLASH)).status_code == 200
    javob = client.post(reverse(TANLASH), {"av": [ikki.pk]})  # ro'yxatdagi tanlov formasi
    assert [e["av"].pk for e in javob.context["elementlar"]] == [ikki.pk]


def test_tanlash_bolim(client_rol, filial_a):
    from vositalar.models import Bolim
    from vositalar.tests.test_bayroqlar import qator

    client = client_rol("hisobchi")
    bolim = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    ichkarida, tashqarida = av_yarat(filial_a, inv="1"), av_yarat(filial_a, inv="2")
    qator(ichkarida, filial_a, bolim=bolim)
    javob = client.get(reverse(TANLASH), {"bolim": bolim.pk})
    assert [e["av"].pk for e in javob.context["elementlar"]] == [ichkarida.pk]
    assert client.get(reverse(TANLASH), {"bolim": "x"}).context["elementlar"] == []


def test_royxat_va_kartochkada_havola(client_rol, filial_a):
    client = client_rol("hisobchi")
    av = av_yarat(filial_a, inv="1")
    assert reverse(TANLASH) in client.get(reverse("vositalar:royxat")).content.decode()
    assert f"{reverse(TANLASH)}?av={av.pk}" in client.get(reverse("vositalar:kartochka", args=[av.pk])).content.decode()


def test_uzun_nom_barcha_olchamlarda_bitta_sahifa(filial_a, olcham_40):
    av = qayta(av_yarat(filial_a, inv="LONG-INV-12345"))
    av.nomi = "Juda uzun nomli asosiy vosita " * 4
    for eni, boyi in ((20, 15), (40, 30), (50, 25), (58, 40)):
        olcham = YorliqOlchami(nomi="t", eni_mm=Decimal(eni), boyi_mm=Decimal(boyi))
        assert len(sahifalar(servis.yorliq_pdf([(av, 2)], olcham))) == 2


def test_hr_yorliq_403(client_rol, filial_a, olcham_40):
    client = client_rol("hr")
    av = av_yarat(filial_a, inv="1")
    assert client.get(reverse(TANLASH), {"av": av.pk}).status_code == 403
    assert client.post(reverse(PDF), {"av": [av.pk], "olcham": olcham_40.pk}).status_code == 403
