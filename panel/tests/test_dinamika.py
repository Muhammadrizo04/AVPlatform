"""Bosh sahifa: filiallar kesimida AV summasi dinamikasi (1C harakatlaridan oyma-oy tiklanadi)."""
import uuid
from datetime import date, datetime, time

import pytest
from django.http import QueryDict
from django.urls import reverse
from django.utils import timezone

from onec.models import Harakat1C
from panel.dinamika import RANGLAR, filial_dinamikasi, oy_qosh
from vositalar.tests.test_bayroqlar import av_yarat

pytestmark = pytest.mark.django_db
JORIY = timezone.localdate().replace(day=1)


def harakat(av, filial, vid, oy: date, summa):
    return Harakat1C.objects.create(
        sana=timezone.make_aware(datetime.combine(oy.replace(day=10), time(12))), hujjat_turi="ПоступлениеОС",
        hujjat_ref=uuid.uuid4(), av=av, filial=filial, vid=vid, soni=1, summa=summa,
    )


@pytest.fixture
def muhit(filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    av = av_yarat(a)
    harakat(av, a, "kirim", oy_qosh(JORIY, -20), 1000)  # davrdan oldin — boshlang'ich summa
    harakat(av, a, "kirim", oy_qosh(JORIY, -3), 500)
    harakat(av, a, "chiqim", oy_qosh(JORIY, -1), 200)
    harakat(av, b, "kirim", oy_qosh(JORIY, -2), 300)
    return a, b


def test_oyma_oy_summa_va_jadval(muhit, foydalanuvchi):
    a, b = muhit
    d = filial_dinamikasi(foydalanuvchi("admin"), QueryDict(f"dan={oy_qosh(JORIY, -5):%Y-%m}&gacha={JORIY:%Y-%m}"))
    assert len(d.oylar) == 6 and d.ogohlantirishlar == []
    seriya = {s["nomi"]: [int(v) for v in s["qiymatlar"]] for s in d.seriyalar}
    assert seriya[a.nomi] == [1000, 1000, 1500, 1500, 1300, 1300]
    assert seriya[b.nomi] == [0, 0, 0, 300, 300, 300]
    jadval = {q["nomi"]: (q["boshi"], q["oxiri"], q["farq"]) for q in d.jadval}
    assert jadval[a.nomi] == (1000, 1300, 300) and jadval[b.nomi] == (0, 300, 300)
    assert (d.jami["boshi"], d.jami["oxiri"], d.jami["foiz"]) == (1000, 1600, 60)
    assert d.tanlangan_jami == d.jami  # standart: eng katta 5 ta = ikkala filial


@pytest.mark.parametrize("dan, gacha, oylar, ogoh", [
    (-2, 0, 6, "kamida 6 oy"),  # juda qisqa — 6 oyga cho'ziladi
    (-80, 0, 60, "5 yil"),  # juda uzun — 5 yilga qisqaradi
    (0, -7, 8, None),  # teskari — almashtiriladi
])
def test_davr_chegaralari(muhit, foydalanuvchi, dan, gacha, oylar, ogoh):
    d = filial_dinamikasi(foydalanuvchi("admin"),
                          QueryDict(f"dan={oy_qosh(JORIY, dan):%Y-%m}&gacha={oy_qosh(JORIY, gacha):%Y-%m}"))
    assert len(d.oylar) == oylar
    if ogoh:
        assert any(ogoh in o for o in d.ogohlantirishlar)


def test_filial_cheklovi(muhit, foydalanuvchi):
    a, b = muhit
    d = filial_dinamikasi(foydalanuvchi("rahbar", filiallar=[b]), QueryDict())
    assert [q["nomi"] for q in d.jadval] == [b.nomi] and d.jami["oxiri"] == 300


def test_bosh_sahifada_va_htmx(muhit, client_rol):
    admin = client_rol("admin")
    html = admin.get(reverse("panel:bosh")).content.decode()
    assert "AV summasi dinamikasi" in html and "data-dinamika" in html and 'id="dinamika-malumot"' in html
    javob = admin.get(reverse("panel:dinamika"), {"dan": f"{oy_qosh(JORIY, -11):%Y-%m}", "gacha": f"{JORIY:%Y-%m}"})
    assert javob.status_code == 200 and javob.content.decode().lstrip().startswith('<section class="card dinamika"')
    # HR summani ko'rmaydi: bosh sahifada grafik yo'q, bo'lak — 403
    hr = client_rol("hr")
    assert "AV summasi dinamikasi" not in hr.get(reverse("panel:bosh")).content.decode()
    assert hr.get(reverse("panel:dinamika")).status_code == 403


def test_hammasi_tanlansa_kichiklari_boshqalarga_yigiladi(filial_yarat, foydalanuvchi):
    filiallar = [filial_yarat(f"F{i}") for i in range(10)]
    for i, f in enumerate(filiallar):
        harakat(av_yarat(f), f, "kirim", oy_qosh(JORIY, -2), 1000 * (i + 1))
    params = QueryDict(mutable=True)
    params.setlist("f", [str(f.pk) for f in filiallar])
    d = filial_dinamikasi(foydalanuvchi("admin"), params)
    assert d.tanlangan_soni == 10 and len(d.seriyalar) == 8
    boshqa = d.seriyalar[-1]
    assert boshqa["nomi"] == "Boshqa 3 ta filial" and boshqa["id"] is None
    assert int(boshqa["qiymatlar"][-1]) == 1000 + 2000 + 3000  # eng kichik uchtasi
    assert {s["rang"] for s in d.seriyalar[:-1]} == set(RANGLAR[:7])


def test_oy_tanlagich_va_filial_tugmalari(muhit, client_rol):
    html = client_rol("admin").get(reverse("panel:dinamika")).content.decode()
    assert html.count("data-oy-tanlov") == 2 and 'name="dan"' in html and 'type="month"' not in html
    assert "data-filial-hammasi" in html and "data-filial-tozala" in html and 'hx-trigger="submit"' in html


def test_umumiy_korish_bitta_chiziq(muhit, foydalanuvchi, client_rol):
    a, b = muhit
    params = QueryDict(f"dan={oy_qosh(JORIY, -5):%Y-%m}&gacha={JORIY:%Y-%m}&umumiy=1", mutable=True)
    d = filial_dinamikasi(foydalanuvchi("admin"), params)
    assert d.umumiy and d.grafik["umumiy"] and len(d.seriyalar) == 1
    assert d.seriyalar[0]["nomi"] == "Barcha filiallar"
    assert [int(v) for v in d.seriyalar[0]["qiymatlar"]] == [1000, 1000, 1500, 1800, 1600, 1600]
    params.setlist("f", [str(a.pk)])
    d = filial_dinamikasi(foydalanuvchi("admin"), params)
    assert d.seriyalar[0]["nomi"] == "1 ta filial jami" and int(d.seriyalar[0]["qiymatlar"][-1]) == 1300
    html = client_rol("admin").get(reverse("panel:dinamika"), {"umumiy": "1"}).content.decode()
    assert 'name="umumiy" value="1" checked' in html


def test_tepadagi_raqamlar_tanlangan_filiallar_boyicha(muhit, foydalanuvchi):
    a, b = muhit
    params = QueryDict(f"dan={oy_qosh(JORIY, -5):%Y-%m}&gacha={JORIY:%Y-%m}", mutable=True)
    params.setlist("f", [str(b.pk)])
    d = filial_dinamikasi(foydalanuvchi("admin"), params)
    assert (d.tanlangan_jami["boshi"], d.tanlangan_jami["oxiri"]) == (0, 300)
    assert d.jami["oxiri"] == 1600  # jadval ostidagi «Jami» — barcha filiallar
