import html
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from onec.models import SinxronJurnal
from vositalar.amortizatsiya import oy_qosh
from vositalar.bayroqlar import BAYROQLAR
from vositalar.models import AVKartochka
from vositalar.tests.test_bayroqlar import av_yarat


@pytest.fixture
def client_hisobchi(client_rol):
    """Bosh sahifani ko'radigan to'liq huquqli rol (hisobchida bosh sahifa yo'q — AV ro'yxatiga o'tadi)."""
    return client_rol("admin")


def test_bosh_filial_kesimi(client_hisobchi, filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    av_yarat(a, soni="2")  # summa 100, kartochkasiz — summa o'zgarishsiz
    av2 = av_yarat(b, soni="3")  # summa 100
    # 12 oy o'tgan, muddat 24 oy -> eskirish 50%
    AVKartochka.objects.create(av=av2, ishga_tushgan_sana=oy_qosh(timezone.localdate(), -12), xizmat_muddati_oy=24)
    javob = client_hisobchi.get(reverse("panel:bosh"))
    assert javob.status_code == 200
    qatorlar = {q["filial"].kod: q for q in javob.context["filiallar"]}
    assert qatorlar["A"]["soni"] == Decimal("2")
    assert qatorlar["A"]["boshlangich"] == Decimal("100")
    assert qatorlar["A"]["qoldiq"] == Decimal("100")
    assert qatorlar["B"]["soni"] == Decimal("3")
    assert qatorlar["B"]["boshlangich"] == Decimal("100")
    assert qatorlar["B"]["qoldiq"] == Decimal("50.00")
    assert javob.context["jami"] == {"soni": Decimal("5"), "boshlangich": Decimal("200"), "qoldiq": Decimal("150.00")}
    html = javob.content.decode()
    assert "<th>Jami</th>" in html
    assert "<th class=\"son\">5</th>" in html and "200,00" in html and "150,00" in html


def test_bosh_sonlar_mingliklar_bilan(client_hisobchi, filial_yarat):
    av = av_yarat(filial_yarat("A"), soni="1108")
    av.qoldiqlar.update(summa=Decimal("3485037435.36"))
    html = client_hisobchi.get(reverse("panel:bosh")).content.decode()
    assert "1\xa0108<" in html
    assert "3\xa0485\xa0037\xa0435,36" in html
    assert "1108,000" not in html


def test_bosh_filial_cheklovi(foydalanuvchi, filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    av_yarat(a)
    av_yarat(b)
    client = Client()
    client.force_login(foydalanuvchi("admin", [a]))
    javob = client.get(reverse("panel:bosh"))
    assert [q["filial"].kod for q in javob.context["filiallar"]] == ["A"]


def test_bosh_bayroq_kartochkalari(client_hisobchi, filial_yarat):
    a = filial_yarat("A")
    av_yarat(a, inv="")  # inv_bosh
    javob = client_hisobchi.get(reverse("panel:bosh"))
    matn = javob.content.decode()
    kartochkalar = {k["kalit"]: k for k in javob.context["bayroqlar"]}
    assert set(kartochkalar) == set(BAYROQLAR)
    assert kartochkalar["inv_bosh"]["soni"] == 1
    for kalit in BAYROQLAR:
        if kalit == "chiqim_kutilmoqda":  # AV ro'yxati emas, chiqimlar ro'yxatiga olib boradi
            assert f'href="{reverse("chiqimlar:royxat")}"' in matn
            continue
        assert f"{reverse('vositalar:royxat')}?bayroq={kalit}" in matn


def _xatolar(n):
    for i in range(n):
        SinxronJurnal.objects.create(
            boshlandi=datetime(2026, 10, 17, 10, i, tzinfo=dt_timezone.utc), natija=SinxronJurnal.Natija.XATO
        )


def test_sinxron_banner_qizil(client_hisobchi):
    _xatolar(3)
    javob = client_hisobchi.get(reverse("panel:bosh"))
    assert javob.context["sinxron_holati"]["xato"] is True
    assert "1C bilan aloqa yo'q" in html.unescape(javob.content.decode())


def test_sinxron_banner_ikki_xatoda_yoq(client_hisobchi):
    _xatolar(2)
    javob = client_hisobchi.get(reverse("panel:bosh"))
    assert javob.context["sinxron_holati"]["xato"] is False
    assert "1C bilan aloqa yo'q" not in html.unescape(javob.content.decode())


def test_sinxron_banner_kulrang_oxirgi_vaqt(client_hisobchi):
    SinxronJurnal.objects.create(
        boshlandi=datetime(2026, 10, 17, 10, 0, tzinfo=dt_timezone.utc),
        tugadi=datetime(2026, 10, 17, 10, 1, tzinfo=dt_timezone.utc),
        natija=SinxronJurnal.Natija.OK,
    )
    matn = html.unescape(client_hisobchi.get(reverse("panel:bosh")).content.decode())
    assert "Oxirgi muvaffaqiyatli sinxron:" in matn


def test_bosh_qiymat_grafiklari(client_hisobchi, client_rol, filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    av_yarat(a, soni="2")  # summa 100
    av2 = av_yarat(b, soni="3")  # summa 100, eskirish 50%
    AVKartochka.objects.create(av=av2, ishga_tushgan_sana=oy_qosh(timezone.localdate(), -12), xizmat_muddati_oy=24)

    javob = client_hisobchi.get(reverse("panel:bosh"))
    grafik = {q["filial"].kod: q for q in javob.context["qiymat_filial"]}
    assert (grafik["A"]["ulush"], grafik["A"]["qoldiq_ulush"]) == (100, 100)
    assert (grafik["B"]["ulush"], grafik["B"]["qoldiq_ulush"]) == (100, 50)
    assert javob.context["eskirish_foizi"] == 25
    assert [q["boshlangich"] for q in javob.context["qiymat_tur"]] == [Decimal("200")]
    html = javob.content.decode()
    assert "Filiallar bo'yicha qiymat" in html.replace("&#x27;", "'") and "AV turlari" in html

    # HR summani ko'rmaydi — grafiklar yo'q
    javob = client_rol("hr").get(reverse("panel:bosh"))
    assert "qiymat_filial" not in javob.context and "bo&#x27;yicha qiymat" not in javob.content.decode()


@pytest.mark.parametrize("qiymat, kutilgan", [
    (Decimal("14889668651.05"), "14,89\xa0mlrd"), (Decimal("123456789"), "123,5\xa0mln"), (Decimal("2000000"), "2\xa0mln"),
    (Decimal("95000.4"), "95\xa0000"), (None, ""),
])
def test_qisqa_pul(qiymat, kutilgan):
    from panel.templatetags.raqamlar import qisqa_pul

    assert qisqa_pul(qiymat) == kutilgan


def test_csrf_skripti_panel_va_mobil_sahifalarda(client_hisobchi, client_rol):
    """HTMX CSRF tokeni har so'rovda cookie'dan olinadi (eski ochiq sahifa ham ishlaydi)."""
    assert "panel/csrf.js" in client_hisobchi.get(reverse("panel:bosh")).content.decode()
    assert "panel/csrf.js" in client_rol("revizor").get(reverse("reviziya:mobil")).content.decode()


def test_csrf_rad_etilsa_tushunarli_sahifa(foydalanuvchi):
    """Eskirgan token bilan oddiy forma yuborilsa — Django texnik sahifasi o'rniga o'zbekcha izoh va qaytish havolasi."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(foydalanuvchi("revizor"))
    javob = client.post(reverse("reviziya:mobil_yangi"), {}, HTTP_REFERER="/reviziya/m/")
    assert javob.status_code == 403
    matn = javob.content.decode()
    assert "Sahifa eskirgan" in matn and "CSRF" in matn
    assert 'href="/reviziya/m/"' in matn


def test_csrf_skripti_oddiy_formalar_tokenini_yangilaydi():
    """Oddiy (HTMX'siz) POST formalarda ham yuborishdan oldin token cookie'dan olinadi."""
    from django.contrib.staticfiles import finders

    with open(finders.find("panel/csrf.js"), encoding="utf-8") as f:
        assert "csrfmiddlewaretoken" in f.read()


def test_tasdiq_oynasi_hamma_sahifada_va_tizim_confirm_qolmagan(client_hisobchi, client_rol):
    """Tasdiqlash — ekran o'rtasidagi o'z oynamiz (tasdiq.js); shablonlarda brauzer confirm() ishlatilmaydi."""
    import pathlib

    assert "panel/tasdiq.js" in client_hisobchi.get(reverse("panel:bosh")).content.decode()
    assert "panel/tasdiq.js" in client_rol("revizor").get(reverse("reviziya:mobil")).content.decode()
    ildiz = pathlib.Path(__file__).resolve().parents[2]
    qolgan = [str(p) for p in ildiz.glob("*/templates/**/*.html") if "confirm(" in p.read_text(encoding="utf-8")]
    assert qolgan == []


def test_mol_qisqartmasi_korinadigan_matnlarda_yoq():
    """«МОЛ» (kirillcha qisqartma) o'rniga «Javobgar shaxs»: shablonlarda ko'rinadigan matn sifatida qolmagan."""
    import pathlib
    import re

    ildiz = pathlib.Path(__file__).resolve().parents[2]
    qolgan = []
    for p in ildiz.glob("*/templates/**/*.html"):
        matn = re.sub(r"{#.*?#}", "", p.read_text(encoding="utf-8"), flags=re.S)
        if "МОЛ" in matn:
            qolgan.append(str(p))
    assert qolgan == []
