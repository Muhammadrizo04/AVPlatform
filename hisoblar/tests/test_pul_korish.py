"""Pul (summa, qiymat, amortizatsiya) faqat `pul_korish` huquqi borlarga: admin, hisobchi, rahbar. HR — faqat soni."""
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from pypdf import PdfReader

from chiqimlar.models import ChiqimHujjat
from hisoblar.huquqlar import huquqi_bor
from jurnal.models import Jurnal
from mol.servis import akt_yarat
from onec.models import AV, AVQoldiq, Harakat1C, Xodim
from vositalar.models import AVKartochka, Holat, Taqsimot

SUMMA = Decimal("987654.32")
KORINISHLAR = ("987 654,32", "987654.32", "987654,32")  # formatlangan va xom ko'rinishlari
DONA = "493 827,16"  # 987654.32 / 2


@pytest.fixture
def dunyo(filial_yarat, foydalanuvchi):
    filial = filial_yarat("A")
    av = AV.objects.create(
        ref_1c=uuid.uuid4(), kod="1", nomi="Noutbuk", inv_raqam="INV-1", filial_rekvizit=filial,
        izoh_1c="Karta 5614 6821 2875 4530 orqali to'landi",
    )
    AVQoldiq.objects.create(av=av, filial=filial, soni=Decimal("2"), summa=SUMMA)
    bobur = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Bobur", filial=filial)
    aziz = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Aziz", filial=filial)
    t = Taqsimot.objects.create(av=av, filial=filial, mol=bobur, holat=Holat.ISHLATILMOQDA, soni=Decimal("2"))
    # 1 yildan keyin muddati tugaydigan AV — xizmat muddati hisobotida chiqadi.
    AVKartochka.objects.create(
        av=av, ishga_tushgan_sana=timezone.localdate() - timedelta(days=365 * 3), xizmat_muddati_oy=36
    )
    Harakat1C.objects.create(
        av=av, filial=filial, sana=timezone.now(), vid=Harakat1C.Vid.KIRIM, hujjat_turi="ПоступлениеОС",
        hujjat_raqami="P-1", hujjat_ref=uuid.uuid4(), soni=Decimal("2"), summa=SUMMA,
    )
    akt = akt_yarat(bobur, aziz, [(t, Decimal("1"))], kim=foydalanuvchi("admin"))
    chiqim = ChiqimHujjat.objects.create(
        hujjat_turi="Реализация", hujjat_raqami="R-1", hujjat_ref=uuid.uuid4(), sana=timezone.now(), av=av,
        filial=filial, soni=Decimal("1"), summa=SUMMA, taxmin_tur="sotildi",
    )
    return {"av": av, "xodim": bobur, "akt": akt, "chiqim": chiqim}


def _client(foydalanuvchi, rol):
    c = Client()
    c.force_login(foydalanuvchi(rol))
    return c


def _sahifalar(d):
    return [
        reverse("panel:bosh"),
        reverse("vositalar:royxat"),
        reverse("vositalar:kartochka", args=[d["av"].pk]),
        reverse("mol:xodimlar"),
        reverse("mol:xodim", args=[d["xodim"].pk]),
        reverse("mol:akt", args=[d["akt"].pk]),
        reverse("chiqimlar:royxat"),
        reverse("chiqimlar:tasdiqlash", args=[d["chiqim"].pk]),
        reverse("hisobotlar:kesim"),
        reverse("hisobotlar:mol_qaydnoma"),
        reverse("hisobotlar:muddat"),
    ]


def _pul_bor(matn: str) -> bool:
    matn = matn.replace("\xa0", " ")  # `pul` filtri mingliklarni bo'linmas bo'sh joy bilan ajratadi
    return any(k in matn for k in KORINISHLAR) or DONA in matn


def test_huquq_rollar(foydalanuvchi):
    assert huquqi_bor(foydalanuvchi("admin"), "pul_korish")
    assert huquqi_bor(foydalanuvchi("hisobchi"), "pul_korish")
    assert huquqi_bor(foydalanuvchi("rahbar"), "pul_korish")
    assert not huquqi_bor(foydalanuvchi("hr"), "pul_korish")


def test_hr_sahifalarda_pul_yoq(foydalanuvchi, dunyo):
    c = _client(foydalanuvchi, "hr")
    for url in _sahifalar(dunyo):
        javob = c.get(url)
        assert javob.status_code == 200, url
        assert not _pul_bor(javob.content.decode()), url


@pytest.mark.parametrize("rol", ["hisobchi", "rahbar"])
def test_pul_huquqi_borlar_korishadi(foydalanuvchi, dunyo, rol):
    c = _client(foydalanuvchi, rol)
    for url in [reverse("vositalar:royxat"), reverse("vositalar:kartochka", args=[dunyo["av"].pk]),
                reverse("chiqimlar:royxat"), reverse("mol:akt", args=[dunyo["akt"].pk])]:
        assert _pul_bor(c.get(url).content.decode()), url


def _xlsx_matni(javob) -> str:
    kitob = load_workbook(io.BytesIO(javob.content), read_only=True)
    return " ".join(str(v) for qator in kitob.active.iter_rows(values_only=True) for v in qator if v is not None)


@pytest.mark.parametrize("url_nomi,parametr", [
    ("vositalar:royxat_excel", {}),
    ("hisobotlar:kesim", {"format": "xlsx"}),
    ("hisobotlar:mol_qaydnoma", {"format": "xlsx"}),
    ("hisobotlar:muddat", {"format": "xlsx"}),
])
def test_hr_excelda_pul_yoq(foydalanuvchi, dunyo, url_nomi, parametr):
    hr = _client(foydalanuvchi, "hr").get(reverse(url_nomi), parametr)
    assert hr.status_code == 200
    matn = _xlsx_matni(hr)
    assert "987654" not in matn and "Summa" not in matn and "qiymat" not in matn.lower()
    hisobchi = _xlsx_matni(_client(foydalanuvchi, "hisobchi").get(reverse(url_nomi), parametr))
    assert "Summa" in hisobchi or "qiymat" in hisobchi.lower()


def _pdf_matni(javob) -> str:
    return " ".join(sahifa.extract_text() for sahifa in PdfReader(io.BytesIO(javob.content)).pages)


def test_hr_akt_pdfda_pul_yoq(foydalanuvchi, dunyo):
    url = reverse("mol:akt_pdf", args=[dunyo["akt"].pk])
    hr = _pdf_matni(_client(foydalanuvchi, "hr").get(url))
    assert "Noutbuk" in hr and "493827" not in hr and "Qiymat" not in hr
    assert "493 827,16" in _pdf_matni(_client(foydalanuvchi, "hisobchi").get(url)).replace(" ", " ")


def test_izoh_1c_hrdan_yashirin_va_karta_niqoblangan(foydalanuvchi, dunyo):
    url = reverse("vositalar:kartochka", args=[dunyo["av"].pk])
    hr = _client(foydalanuvchi, "hr").get(url).content.decode()
    assert "to'landi" not in hr and "4530" not in hr
    hisobchi = _client(foydalanuvchi, "hisobchi").get(url).content.decode()
    assert "orqali to" in hisobchi  # izoh ko'rinadi
    assert "5614 6821 2875" not in hisobchi and "4530" in hisobchi  # faqat oxirgi 4 raqam


def test_karta_niqobi_filtri():
    from panel.templatetags.raqamlar import karta_niqobi

    assert karta_niqobi("5614 6821 2875 4530 Ali") == "**** **** **** 4530 Ali"
    assert karta_niqobi("8600123456789012") == "**** **** **** 9012"
    assert karta_niqobi("tel 99 932 07 01") == "tel 99 932 07 01"  # telefon raqami tegilmaydi
    assert karta_niqobi("") == ""


def test_hr_tarixda_summa_yoq(foydalanuvchi, dunyo):
    Jurnal.objects.create(
        kim_nomi="admin", obyekt_turi="vositalar.avkartochka",
        obyekt_id=str(AVKartochka.objects.get(av=dunyo["av"]).pk), maydon="ishga_tushgan_sana", eski="", yangi="2026-01-24",
    )
    url = reverse("vositalar:kartochka", args=[dunyo["av"].pk])
    html = _client(foydalanuvchi, "hr").get(url).content.decode()
    assert "Ishga tushgan sana" in html and "ishga_tushgan_sana:" not in html  # maydon nomi odam tilida
