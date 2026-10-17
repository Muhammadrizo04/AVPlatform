"""So'rov parametrlari: `son()`, NUL bayt middleware'i, noto'g'ri qiymatlar 500 bermasligi, HTTPS sozlamalari,
rahbar POST -> 403."""
import runpy
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

from hisoblar.parametrlar import son
from mol.models import MolAkt
from onec.models import Xodim
from vositalar.models import Bolim, Rasm
from vositalar.tests.test_bayroqlar import av_yarat, qator

NOTOGRI = ["²", "1" * 5000, "9" * 19, "abc", "\x00", "-1", "1.5", " "]


@pytest.mark.parametrize(
    "qiymat,kutilgan",
    [
        ("12", 12), (" 7 ", 7), ("0", 0), ("9" * 18, int("9" * 18)), (5, 5), (None, None), ("", None),
        ("²", None), ("١٢", None), ("1" * 5000, None), ("9" * 19, None), ("abc", None), ("-1", None),
        ("1.5", None), ("1e3", None), ("\x00", None), ("1\x00", None),
    ],
)
def test_son(qiymat, kutilgan):
    assert son(qiymat) == kutilgan


@pytest.fixture
def muhit(foydalanuvchi, filial_yarat):
    """Admin client, bitta AV (taqsimot qatori, bo'lim, xodim bilan)."""
    filial = filial_yarat("A")
    av = av_yarat(filial, soni="2")
    bolim = Bolim.objects.create(filial=filial, nomi="Ombor")
    ali = Xodim.objects.create(ref_1c="00000000-0000-0000-0000-000000000001", ism="Ali", filial=filial)
    t = qator(av, filial, "2", mol=ali)
    c = Client()
    c.force_login(foydalanuvchi("admin"))
    return {"c": c, "av": av, "bolim": bolim, "filial": filial, "xodim": ali, "qator": t}


def _sorovlar(m, x):
    """(metod, url, ma'lumot, qo'shimcha sarlavhalar) — har bir parametr alohida `x` bilan."""
    av, b, f, t = m["av"], m["bolim"], m["filial"], m["qator"]
    royxat = reverse("vositalar:royxat")
    sorovlar = []
    for kalit in ("q", "holat", "filial", "bolim", "turi", "mol", "page", "bayroq"):
        sorovlar += [
            ("get", royxat, {kalit: x}, {}),
            ("get", royxat, {kalit: x}, {"HTTP_HX_REQUEST": "true"}),
            ("get", reverse("vositalar:royxat_excel"), {kalit: x}, {}),
        ]
    sorovlar += [
        ("post", reverse("vositalar:ommaviy"), {"amal": "kochirish", "bolim": x, "av": [x, av.pk]}, {}),
        ("post", reverse("vositalar:ommaviy"), {"amal": "kochirish", "bolim": b.pk, "av": x}, {}),
        ("post", reverse("vositalar:kartochka", args=[av.pk]), {"xizmat_muddati_oy": x, "versiya": "0"}, {}),
        ("post", reverse("vositalar:kartochka", args=[av.pk]), {"versiya": x}, {}),
        ("post", reverse("vositalar:kartochka", args=[av.pk]), {"versiya": "0", "izoh": f"a{x}"}, {}),
        ("post", reverse("vositalar:taqsimot_amal", args=[av.pk]), {"qator": x, "amal": "holat"}, {}),
        ("post", reverse("vositalar:taqsimot_amal", args=[av.pk]), {"qator": t.pk, "amal": "kochir", "bolim": x}, {}),
        ("post", reverse("vositalar:taqsimot_amal", args=[av.pk]), {"qator": t.pk, "amal": "kochir", "soni": x}, {}),
        ("post", reverse("vositalar:rasm_asosiy", args=[av.pk]), {"rasm": x}, {}),
        ("get", reverse("vositalar:bolimlar"), {"filial": x}, {}),
        ("get", reverse("vositalar:bolimlar"), {"filial": f.pk, "bolim": x}, {}),
        ("post", reverse("vositalar:bolim_saqla"), {"filial": x, "nomi": "Yangi"}, {}),
        ("post", reverse("vositalar:bolim_saqla"), {"filial": f.pk, "bolim": x, "nomi": "Yangi"}, {}),
        ("post", reverse("vositalar:bolim_saqla"), {"filial": f.pk, "ota": x, "nomi": "Yangi"}, {}),
        ("post", reverse("vositalar:bolim_saqla"), {"filial": f.pk, "nomi": f"Yangi{x}"}, {}),
        ("get", reverse("mol:akt_yangi"), {"topshiruvchi": x}, {}),
        ("post", reverse("mol:akt_yangi"), {"topshiruvchi": x, "qabul": m["xodim"].pk}, {}),
        ("post", reverse("mol:akt_yangi"), {"topshiruvchi": m["xodim"].pk, "qabul": x, "tanlangan": [t.pk]}, {}),
        ("post", reverse("mol:akt_yangi"), {"topshiruvchi": m["xodim"].pk, "qabul": m["xodim"].pk, "tanlangan": x}, {}),
        ("post", reverse("mol:akt_yangi"), {"topshiruvchi": m["xodim"].pk, "tanlangan": [t.pk], f"soni_{t.pk}": x}, {}),
        ("post", reverse("mol:akt_yangi"), {"topshiruvchi": "", "qabul": m["xodim"].pk, "izoh": f"a{x}"}, {}),
        ("get", reverse("yorliqlar:tanlash"), {"av": x}, {}),
        ("get", reverse("yorliqlar:tanlash"), {"bolim": x}, {}),
        ("post", reverse("yorliqlar:pdf"), {"olcham": x, "av": av.pk}, {}),
        ("post", reverse("yorliqlar:pdf"), {"olcham": "1", "av": x}, {}),
        ("get", reverse("hisobotlar:mol_qaydnoma"), {"xodim": x}, {}),
    ]
    return sorovlar


@pytest.mark.parametrize("x", NOTOGRI, ids=["unicode", "5000", "19", "abc", "nul", "manfiy", "kasr", "bosh"])
def test_notogri_qiymatlar_500_bermaydi(muhit, x):
    c = muhit["c"]
    for metod, url, malumot, sarlavha in _sorovlar(muhit, x):
        # Test client 500 bo'lsa istisnoni qayta ko'taradi; qo'shimcha ravishda status tekshiriladi.
        javob = getattr(c, metod)(url, malumot, **sarlavha)
        assert javob.status_code < 500, (metod, url, malumot)
        if "\x00" in x:
            assert javob.status_code == 400, (metod, url, malumot)
    assert not MolAkt.objects.exists()


def test_notogri_qiymat_xulqi_saqlanadi(muhit):
    c, av = muhit["c"], muhit["av"]
    url = reverse("vositalar:taqsimot_amal", args=[av.pk])
    assert c.post(url, {"qator": "²", "amal": "holat"}).status_code == 404
    assert c.post(url, {"qator": muhit["qator"].pk, "amal": "kochir", "bolim": "²"}).status_code == 400
    assert c.get(reverse("vositalar:bolimlar"), {"filial": "9" * 19}).status_code == 404
    assert c.post(reverse("vositalar:bolim_saqla"), {"filial": "abc", "nomi": "X"}).status_code == 404
    assert c.get(reverse("mol:akt_yangi"), {"topshiruvchi": "²"}).status_code == 404
    from vositalar.models import AVKartochka

    versiya = AVKartochka.objects.get_or_create(av=av)[0].versiya
    javob = c.post(reverse("vositalar:kartochka", args=[av.pk]), {"xizmat_muddati_oy": "²", "versiya": versiya})
    assert javob.status_code == 400 and "1 dan 1200 gacha" in javob.content.decode()
    # Noto'g'ri filtr qiymati e'tiborga olinmaydi (ro'yxat to'liq).
    javob = c.get(reverse("vositalar:royxat"), {"filial": "²"})
    assert [a.pk for a in javob.context["sahifa"]] == [av.pk]


def test_nul_bayt_kalitda_ham_400(muhit):
    assert muhit["c"].get(reverse("vositalar:royxat"), {"a\x00": "1"}).status_code == 400
    assert muhit["c"].post(reverse("vositalar:ommaviy"), {"amal\x00": "x"}).status_code == 400


# ---------- rahbar: o'zgartirish amallari 403 ----------

def test_rahbar_post_403(client_rol, filial_yarat):
    filial = filial_yarat("A")
    av = av_yarat(filial)
    t = qator(av, filial, "1")
    bolim = Bolim.objects.create(filial=filial, nomi="Ombor")
    c = client_rol("rahbar")
    sorovlar = [
        (reverse("vositalar:taqsimot_amal", args=[av.pk]), {"qator": t.pk, "amal": "holat", "holat": "nosoz"}),
        (reverse("vositalar:kartochka", args=[av.pk]), {"versiya": "0", "izoh": "x"}),
        (reverse("vositalar:rasm_yukla", args=[av.pk]), {}),
        (reverse("vositalar:bolim_saqla"), {"filial": filial.pk, "nomi": "Yangi"}),
        (reverse("vositalar:bolim_nofaol", args=[bolim.pk]), {}),
    ]
    for url, malumot in sorovlar:
        assert c.post(url, malumot).status_code == 403, url
    assert c.get(reverse("vositalar:kartochka", args=[av.pk])).status_code == 200
    t.refresh_from_db()
    bolim.refresh_from_db()
    assert t.holat == "ishlatilmoqda" and bolim.faol
    assert not Bolim.objects.filter(nomi="Yangi").exists() and not Rasm.objects.exists()


# ---------- HTTPS sozlamalari ----------

SOZLAMALAR = Path(__file__).resolve().parents[2] / "config" / "settings.py"


def _sozlamalar(monkeypatch, **muhit):
    for kalit in ("HTTPS", "CSRF_TRUSTED_ORIGINS", "ALLOWED_HOSTS"):
        monkeypatch.delenv(kalit, raising=False)
    for kalit, qiymat in muhit.items():
        monkeypatch.setenv(kalit, qiymat)
    return runpy.run_path(str(SOZLAMALAR))


def test_https_yoqilgan(monkeypatch):
    s = _sozlamalar(monkeypatch, HTTPS="True", ALLOWED_HOSTS="av.example.uz,.example.uz,*")
    assert s["SECURE_PROXY_SSL_HEADER"] == ("HTTP_X_FORWARDED_PROTO", "https")
    assert s["SESSION_COOKIE_SECURE"] is True and s["CSRF_COOKIE_SECURE"] is True
    assert s["SECURE_HSTS_SECONDS"] == 31536000
    assert s["CSRF_TRUSTED_ORIGINS"] == ["https://av.example.uz", "https://example.uz"]


def test_https_ishonchli_manbalar_envdan(monkeypatch):
    s = _sozlamalar(
        monkeypatch, HTTPS="True", ALLOWED_HOSTS="av.example.uz", CSRF_TRUSTED_ORIGINS="https://a.uz,https://b.uz"
    )
    assert s["CSRF_TRUSTED_ORIGINS"] == ["https://a.uz", "https://b.uz"]


def test_https_standart_ochiq(monkeypatch):
    s = _sozlamalar(monkeypatch, ALLOWED_HOSTS="av.example.uz")
    assert s["HTTPS"] is False
    for kalit in ("SECURE_PROXY_SSL_HEADER", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_HSTS_SECONDS"):
        assert kalit not in s
