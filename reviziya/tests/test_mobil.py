import html
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from reviziya.models import ReviziyaQayd
from reviziya.servis import qayd_qosh, reviziya_och, yakunla
from vositalar.models import Bolim, Rasm
from vositalar.tests.test_bayroqlar import av_yarat, qator
from vositalar.tests.test_kartochka import rasm_baytlari, yuklama

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("07")


@pytest.fixture
def revizor(foydalanuvchi):
    return foydalanuvchi("revizor")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


def kirgan(user):
    c = Client()
    c.force_login(user)
    return c


def matn(javob) -> str:
    return html.unescape(javob.content.decode())


@pytest.fixture
def muhit(fa, revizor, hisobchi):
    """`fa` filiali, «Kabinet» xonasida INV-1 (2 dona) va INV-2 (1 dona); revizor biriktirilgan ochiq reviziya."""
    xona = Bolim.objects.create(filial=fa, nomi="Kabinet")
    stol, stul = av_yarat(fa, inv="INV-1", soni="2"), av_yarat(fa, inv="INV-2")
    qator(stol, fa, "2", bolim=xona)
    qator(stul, fa, "1", bolim=xona)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    return rv, xona, stol, stul


def url(nom, *args, **params):
    manzil = reverse(f"reviziya:{nom}", args=args)
    if params:
        manzil += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return manzil


def saqla(c, rv, xona, **maydonlar):
    data = {"bolim": xona.pk if xona else 0, "soni": "1", "usul": "qidiruv", **maydonlar}
    return c.post(url("mobil_saqla", rv.pk), data)


def test_revizor_kirganda_mobilga(muhit, revizor):
    c = kirgan(revizor)
    javob = c.get("/")
    assert javob.status_code == 302 and javob.url == reverse("reviziya:mobil")
    assert c.get("/av/").status_code == 403
    royxat = c.get(reverse("reviziya:mobil"))
    assert royxat.status_code == 200 and muhit[0].nomi in matn(royxat)


def test_hisobchi_boshda_qoladi(muhit, hisobchi):
    assert kirgan(hisobchi).get("/").status_code == 200


def test_faqat_biriktirilgan(muhit, foydalanuvchi, hisobchi, fa, filial_yarat):
    rv, xona, *_ = muhit
    begona = kirgan(foydalanuvchi("revizor"))
    assert begona.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 404
    assert begona.get(url("mobil_topish", rv.pk, q="INV-1")).status_code == 404
    assert saqla(begona, rv, xona, av=muhit[2].pk).status_code == 404
    assert rv.nomi not in matn(begona.get(reverse("reviziya:mobil")))
    # reviziya_boshqarish — biriktirilmagan bo'lsa ham kiradi; boshqa filialdagi hisobchi — 404
    assert kirgan(hisobchi).get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 200
    boshqa_hisobchi = kirgan(foydalanuvchi("hisobchi", filiallar=[filial_yarat("99")]))
    assert boshqa_hisobchi.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 404
    # HR — reviziya_otkazish yo'q
    assert kirgan(foydalanuvchi("hr")).get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 403
    yakunla(rv, hisobchi)
    c = kirgan(muhit[0].revizorlar.first())
    assert c.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 403
    assert saqla(c, rv, xona, av=muhit[2].pk).status_code == 403
    assert rv.nomi not in matn(c.get(reverse("reviziya:mobil")))


def test_xonalar(muhit, revizor):
    rv, xona, *_ = muhit
    javob = kirgan(revizor).get(url("mobil_xonalar", rv.pk))
    t = matn(javob)
    assert javob.status_code == 200 and "Kabinet" in t and "Bo'limsiz" in t and "0 / 3" in t


def test_skan_xonani_eslab_qoladi(muhit, revizor):
    rv, xona, *_ = muhit
    c = kirgan(revizor)
    assert c.get(url("mobil_skan", rv.pk)).status_code == 302  # xona tanlanmagan
    assert c.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 200
    javob = c.get(url("mobil_skan", rv.pk))
    assert javob.status_code == 200 and "Kabinet" in matn(javob)
    assert c.get(url("mobil_skan", rv.pk, bolim=0)).status_code == 200
    assert c.get(url("mobil_skan", rv.pk, bolim=999999)).status_code == 404


def test_qidiruv_va_saqlash(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    c.get(url("mobil_skan", rv.pk, bolim=xona.pk))
    javob = c.get(url("mobil_topish", rv.pk, q="INV-1"))
    t = matn(javob)
    assert javob.status_code == 200 and stol.nomi in t and "Kutilgan: 2" in t and "guruh × 2" in t
    assert saqla(c, rv, xona, av=stol.pk).status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv, av=stol)
    assert qayd.soni == 1 and qayd.bolim == xona and qayd.usul == "qidiruv" and qayd.kim == revizor
    assert saqla(c, rv, xona, av=stol.pk).status_code == 200
    qayd.refresh_from_db()
    assert qayd.soni == 2 and ReviziyaQayd.objects.count() == 1
    # topilmagan qidiruv
    assert "Hech narsa topilmadi" in matn(c.get(url("mobil_topish", rv.pk, q="YOQ-999")))


def test_boshqa_filial_av_saqlanmaydi(muhit, revizor, filial_yarat):
    rv, xona, *_ = muhit
    begona_av = av_yarat(filial_yarat("55"), inv="INV-X")
    javob = saqla(kirgan(revizor), rv, xona, av=begona_av.pk)
    assert javob.status_code == 400 and not ReviziyaQayd.objects.exists()


def test_qr_orqali_topish(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    c.get(url("mobil_skan", rv.pk, bolim=xona.pk))
    javob = c.get(url("mobil_topish", rv.pk, qr="DS|07|INV-1"))
    assert javob.status_code == 200 and stol.nomi in matn(javob) and 'value="qr"' in matn(javob)
    javob = c.get(url("mobil_topish", rv.pk, qr="abc"))
    assert javob.status_code == 200 and "noma'lum yorliq" in matn(javob).lower()
    assert saqla(c, rv, xona, qr_matn="abc", usul="qr").status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv)
    assert qayd.av is None and qayd.qr_matn == "abc" and qayd.usul == "qr"


def test_uzun_qr_kesiladi(muhit, revizor):
    rv, xona, *_ = muhit
    c = kirgan(revizor)
    uzun = "DS|07|" + "Z" * 294  # 300 belgi
    javob = c.get(reverse("reviziya:mobil_topish", args=[rv.pk]), {"qr": uzun, "bolim": xona.pk})
    assert javob.status_code == 200 and "noma'lum yorliq" in matn(javob).lower()
    assert saqla(c, rv, xona, qr_matn=uzun, usul="qr").status_code == 200
    assert ReviziyaQayd.objects.get(reviziya=rv).qr_matn == uzun[:255]


def test_vergulli_son(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    assert saqla(c, rv, xona, av=stol.pk, soni="1,5").status_code == 200
    assert ReviziyaQayd.objects.get(reviziya=rv).soni == Decimal("1.5")
    for yomon in ("-1", "", "0", "abc", "1000000", "NaN"):
        javob = saqla(c, rv, xona, av=stol.pk, soni=yomon)
        assert javob.status_code == 400, yomon
        assert "son" in matn(javob).lower()
    assert ReviziyaQayd.objects.get(reviziya=rv).soni == Decimal("1.5")


def test_tuzatish(muhit, revizor, foydalanuvchi):
    rv, xona, stol, _ = muhit
    qayd = qayd_qosh(rv, xona, revizor, av=stol)
    c = kirgan(revizor)
    assert c.post(url("mobil_tuzat", qayd.pk), {"soni": "3"}).status_code == 200
    qayd.refresh_from_db()
    assert qayd.soni == 3
    assert c.post(url("mobil_tuzat", qayd.pk), {"soni": "-2"}).status_code == 400
    ikkinchi = foydalanuvchi("revizor")
    rv.revizorlar.add(ikkinchi)
    assert kirgan(ikkinchi).post(url("mobil_tuzat", qayd.pk), {"soni": "1"}).status_code == 400
    assert kirgan(foydalanuvchi("revizor")).post(url("mobil_tuzat", qayd.pk), {"soni": "1"}).status_code == 404
    assert c.post(url("mobil_tuzat", qayd.pk), {"soni": "0"}).status_code == 200
    assert not ReviziyaQayd.objects.exists()


def test_http_da_kamera_izohi(muhit, revizor):
    rv, xona, *_ = muhit
    t = matn(kirgan(revizor).get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "Kamera faqat HTTPS'da ishlaydi — inv. raqamni kiriting" in t
    assert "data-xavfsiz" in t and "skan.js" in t


def test_qolganlar(muhit, revizor):
    rv, xona, stol, stul = muhit
    c = kirgan(revizor)
    t = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "INV-1" in t and "INV-2" in t
    qayd_qosh(rv, xona, revizor, av=stul)
    t = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    qolganlar = t[t.index('id="qolganlar"'):]
    assert "INV-1" in qolganlar and "INV-2" not in qolganlar


def test_rasm_bilan_saqlash(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    javob = saqla(c, rv, xona, av=stol.pk, izoh="Singan", rasm=yuklama(rasm_baytlari(format="PNG"), nom="r.png"))
    assert javob.status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv)
    assert qayd.rasm is not None and qayd.rasm in Rasm.objects.filter(av=stol) and qayd.izoh == "Singan"
    javob = saqla(c, rv, xona, av=stol.pk, rasm=yuklama(b"rasm emas"))
    assert javob.status_code == 400 and "JPEG yoki PNG" in matn(javob)
    qayd.refresh_from_db()
    assert qayd.soni == 1
