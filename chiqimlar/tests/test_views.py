import html
import uuid
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from chiqimlar.models import ChiqimHujjat
from onec.models import AV, AVQoldiq
from vositalar.models import Bolim, Holat, Taqsimot
from vositalar.tarix import tarix

pytestmark = pytest.mark.django_db

SANA = datetime(2026, 9, 10, 12, 0, tzinfo=dt_tz.utc)


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def fb(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def av():
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


def chiqim(av, filial, soni="1", holat="kutilmoqda", raqam="17"):
    return ChiqimHujjat.objects.create(
        hujjat_turi="Реализация", hujjat_raqami=raqam, hujjat_ref=uuid.uuid4(), sana=SANA, av=av, filial=filial,
        soni=Decimal(soni), summa=Decimal("100"), taxmin_tur="sotildi", holat=holat,
    )


def kirgan(foydalanuvchi, rol, filiallar=()):
    c = Client()
    c.force_login(foydalanuvchi(rol, filiallar))
    return c


@pytest.fixture
def tayyor(av, fa):
    AVQoldiq.objects.create(av=av, filial=fa, soni=Decimal("0"), summa=Decimal("0"))
    t = Taqsimot.objects.create(av=av, filial=fa, soni=Decimal("1"))
    return t, chiqim(av, fa)


def test_royxat_standart_kutilmoqda(client_rol, av, fa):
    chiqim(av, fa, raqam="KUT")
    chiqim(av, fa, holat="tasdiqlangan", raqam="TAS")
    r = client_rol("hisobchi").get(reverse("chiqimlar:royxat"))
    assert r.status_code == 200
    html = r.content.decode()
    assert "KUT" in html and "TAS" not in html
    r = client_rol("hisobchi").get(reverse("chiqimlar:royxat"), {"holat": "tasdiqlangan"})
    assert "TAS" in r.content.decode() and "KUT" not in r.content.decode()


def test_royxat_filial_cheklovi(foydalanuvchi, av, fa, fb):
    chiqim(av, fa, raqam="AAA")
    chiqim(av, fb, raqam="BBB")
    html = kirgan(foydalanuvchi, "hisobchi", [fa]).get(reverse("chiqimlar:royxat")).content.decode()
    assert "AAA" in html and "BBB" not in html


@pytest.mark.parametrize("params", [
    {"filial": "²"}, {"filial": "9" * 19}, {"tur": "x"}, {"holat": "x"}, {"dan": "²"}, {"gacha": "xx"}, {"page": "²"},
])
def test_royxat_bad_param_500_yoq(client_rol, params):
    assert client_rol("hisobchi").get(reverse("chiqimlar:royxat"), params).status_code == 200


def test_tasdiqlash_oqimi(foydalanuvchi, tayyor, av):
    t, c = tayyor
    cl = kirgan(foydalanuvchi, "hisobchi")
    url = reverse("chiqimlar:tasdiqlash", args=[c.pk])
    r = cl.get(url)
    assert r.status_code == 200
    assert 'name="kutilgan_soni" value="1"' in r.content.decode()
    r = cl.post(url, {"tur": "sotildi", "kutilgan_soni": "1", f"soni_{t.pk}": "1", "izoh": "ok"})
    assert r.status_code == 302 and r.url == reverse("chiqimlar:royxat")
    c.refresh_from_db()
    assert c.holat == "tasdiqlangan" and c.tur == "sotildi"
    assert any("Sotildi" in q.matn for q in tarix(av, c.kim))


def test_tasdiqlash_otkazish(foydalanuvchi, tayyor, fb):
    t, c = tayyor
    b = Bolim.objects.create(filial=fb, nomi="Ombor")
    cl = kirgan(foydalanuvchi, "hisobchi")
    r = cl.post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), {
        "tur": "otkazish", "kutilgan_soni": "1", f"soni_{t.pk}": "1", "qabul_filial": fb.pk, "b_bolim": b.pk,
        "b_holat": "",
    })
    assert r.status_code == 302
    c.refresh_from_db()
    assert c.qabul_filial == fb


def test_tasdiqlash_xato_400_xabar(foydalanuvchi, tayyor):
    t, c = tayyor
    r = kirgan(foydalanuvchi, "hisobchi").post(
        reverse("chiqimlar:tasdiqlash", args=[c.pk]), {"tur": "sotildi", "kutilgan_soni": "1", f"soni_{t.pk}": "0"}
    )
    assert r.status_code == 400
    assert "yig'indisi" in html.unescape(r.content.decode())
    c.refresh_from_db()
    assert c.holat == "kutilmoqda"


@pytest.mark.parametrize("qiymat", ["abc", "²", "1e999", "NaN"])
def test_tasdiqlash_bad_son_400(foydalanuvchi, tayyor, qiymat):
    t, c = tayyor
    r = kirgan(foydalanuvchi, "hisobchi").post(
        reverse("chiqimlar:tasdiqlash", args=[c.pk]), {"tur": "sotildi", "kutilgan_soni": "1", f"soni_{t.pk}": qiymat}
    )
    assert r.status_code == 400


def test_hr_rahbar_tasdiqlay_olmaydi(foydalanuvchi, tayyor):
    t, c = tayyor
    for rol in ("hr", "rahbar"):
        cl = kirgan(foydalanuvchi, rol)
        assert cl.get(reverse("chiqimlar:royxat")).status_code == 200
        r = cl.post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), {"tur": "sotildi", "kutilgan_soni": "1"})
        assert r.status_code == 403
        r = cl.get(reverse("chiqimlar:tasdiqlash", args=[c.pk]))
        html = r.content.decode()
        assert r.status_code == 200
        assert 'name="tur"' not in html and 'name="kutilgan_soni"' not in html and "Taxmin qilingan tur" in html
    c.refresh_from_db()
    assert c.holat == "kutilmoqda"


@pytest.mark.parametrize("holat,matn", [("tasdiqlangan", "allaqachon tasdiqlangan"), ("bekor", "bekor qilingan")])
def test_post_kutilmoqda_emas_ogohlantirish(foydalanuvchi, av, fa, holat, matn):
    c = chiqim(av, fa, holat=holat)
    r = kirgan(foydalanuvchi, "hisobchi").post(
        reverse("chiqimlar:tasdiqlash", args=[c.pk]), {"tur": "sotildi", "kutilgan_soni": "1"}
    )
    assert r.status_code == 200 and matn in html.unescape(r.content.decode())


def test_ruxsatsiz_filial_chiqimi_404(foydalanuvchi, av, fa, fb):
    c = chiqim(av, fb)
    cl = kirgan(foydalanuvchi, "hisobchi", [fa])
    assert cl.get(reverse("chiqimlar:tasdiqlash", args=[c.pk])).status_code == 404
    assert cl.post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), {"tur": "sotildi"}).status_code == 404


def test_b_filial_ruxsatsiz_rad(foydalanuvchi, tayyor, filial_yarat, fa):
    t, c = tayyor
    fv = filial_yarat("V")
    cl = kirgan(foydalanuvchi, "hisobchi", [fa])
    url = reverse("chiqimlar:tasdiqlash", args=[c.pk])
    # Ruxsatsiz B'ga bo'limsiz o'tkazish mumkin (spec §6.5), B ro'yxatda ko'rinadi.
    assert f'value="{fv.pk}"' in cl.get(url).content.decode()
    bv = Bolim.objects.create(filial=fv, nomi="Ombor")
    r = cl.post(url, {
        "tur": "otkazish", "kutilgan_soni": "1", f"soni_{t.pk}": "1", "qabul_filial": fv.pk, "b_bolim": bv.pk,
    })
    assert r.status_code == 400
    c.refresh_from_db()
    assert c.holat == "kutilmoqda"
    r = cl.post(url, {"tur": "otkazish", "kutilgan_soni": "1", f"soni_{t.pk}": "1", "qabul_filial": fv.pk})
    assert r.status_code == 302
    c.refresh_from_db()
    assert c.holat == "tasdiqlangan" and c.qabul_filial == fv


def test_tasdiqlangan_faqat_oqish(foydalanuvchi, tayyor):
    t, c = tayyor
    cl = kirgan(foydalanuvchi, "hisobchi")
    cl.post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), {"tur": "sotildi", "kutilgan_soni": "1", f"soni_{t.pk}": "1"})
    r = cl.get(reverse("chiqimlar:tasdiqlash", args=[c.pk]))
    assert r.status_code == 200 and 'name="tur"' not in r.content.decode()


def test_bosh_sahifa_kartochka_havolasi(client_rol, av, fa):
    chiqim(av, fa)
    html = client_rol("hisobchi").get(reverse("panel:bosh")).content.decode()
    assert f'href="{reverse("chiqimlar:royxat")}"' in html
    assert "bayroq=chiqim_kutilmoqda" not in html


def test_menyu_nishon(client_rol, av, fa):
    chiqim(av, fa)
    html = client_rol("hisobchi").get(reverse("panel:bosh")).content.decode()
    assert "1C chiqimlari" in html
    assert 'badge bg-danger ms-auto">1<' in html
    for rol in ("hr", "rahbar"):  # tasdiqlay olmaydiganlar: menyu bor, belgi yo'q
        html = client_rol(rol).get(reverse("panel:bosh")).content.decode()
        assert "1C chiqimlari" in html and 'badge bg-danger ms-auto' not in html, rol


def test_kutilgan_soni_yoq_400(foydalanuvchi, tayyor):
    t, c = tayyor
    cl = kirgan(foydalanuvchi, "hisobchi")
    for forma in ({"tur": "sotildi", f"soni_{t.pk}": "1"}, {"tur": "sotildi", "kutilgan_soni": " ", f"soni_{t.pk}": "1"}):
        r = cl.post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), forma)
        assert r.status_code == 400
        assert "o'zgargan" not in html.unescape(r.content.decode())
    c.refresh_from_db()
    assert c.holat == "kutilmoqda"


def test_b_taqsimlanmagan_yoq_ogohlantirish(foydalanuvchi, tayyor, fb):
    t, c = tayyor
    b = Bolim.objects.create(filial=fb, nomi="Ombor")
    cl = kirgan(foydalanuvchi, "hisobchi")
    r = cl.post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), {
        "tur": "otkazish", "kutilgan_soni": "1", f"soni_{t.pk}": "1", "qabul_filial": fb.pk, "b_bolim": b.pk,
    }, follow=True)
    assert "joylandi: 0" in html.unescape(r.content.decode())
    c.refresh_from_db()
    assert c.holat == "tasdiqlangan"


def test_b_joylandi_ogohlantirish_yoq(foydalanuvchi, tayyor, fb, av):
    t, c = tayyor
    b = Bolim.objects.create(filial=fb, nomi="Ombor")
    Taqsimot.objects.create(av=av, filial=fb, soni=Decimal("1"))
    r = kirgan(foydalanuvchi, "hisobchi").post(reverse("chiqimlar:tasdiqlash", args=[c.pk]), {
        "tur": "otkazish", "kutilgan_soni": "1", f"soni_{t.pk}": "1", "qabul_filial": fb.pk, "b_bolim": b.pk,
    }, follow=True)
    assert "joylandi:" not in html.unescape(r.content.decode())


def test_royxat_korinmaydigan_av_oddiy_matn(foydalanuvchi, fa, fb):
    # AV arxivda (A'da qoldiq yo'q) va rekviziti B'da: A'ga ruxsatli foydalanuvchi chiqimni ko'radi, AV'ni emas.
    arxiv_av = AV.objects.create(ref_1c=uuid.uuid4(), kod="9", nomi="ArxivStol", filial_rekvizit=fb)
    chiqim(arxiv_av, fa)
    cl = kirgan(foydalanuvchi, "hisobchi", [fa])
    sahifa = cl.get(reverse("chiqimlar:royxat")).content.decode()
    assert "ArxivStol" in sahifa
    assert reverse("vositalar:kartochka", args=[arxiv_av.pk]) not in sahifa
    # Ruxsat etilgan filial rekviziti bo'lsa — havola bor.
    cl2 = kirgan(foydalanuvchi, "hisobchi", [fa, fb])
    assert reverse("vositalar:kartochka", args=[arxiv_av.pk]) in cl2.get(reverse("chiqimlar:royxat")).content.decode()
