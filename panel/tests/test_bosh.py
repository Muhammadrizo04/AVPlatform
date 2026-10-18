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
    return client_rol("hisobchi")


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
    assert "1 108<" in html
    assert "3 485 037 435,36" in html
    assert "1108,000" not in html


def test_bosh_filial_cheklovi(foydalanuvchi, filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    av_yarat(a)
    av_yarat(b)
    client = Client()
    client.force_login(foydalanuvchi("hisobchi", [a]))
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
