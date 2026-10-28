"""AV ro'yxati qatorida joylashuv (bo'lim, МОЛ, holat), МОЛ ismi bo'yicha qidiruv, bosh sahifa va МОЛ nazorati
rollar bo'yicha."""
import uuid

import pytest
from django.urls import reverse

from onec.models import Xodim
from vositalar.bayroqlar import BAYROQLAR
from vositalar.models import Bolim
from vositalar.tests.test_bayroqlar import av_yarat, qator

ROYXAT = "vositalar:royxat"


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("A")


def _xodim(filial, ism, **kw):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism=ism, filial=filial, **kw)


def test_royxat_qatorida_bolim_mol_holat(client_rol, filial):
    av = av_yarat(filial, soni="3")
    ombor = Bolim.objects.create(filial=filial, nomi="Ombor")
    qator(av, filial, "2", bolim=ombor, mol=_xodim(filial, "Bobur Aliyev"))
    qator(av, filial, "1")
    for htmx in ({}, {"HTTP_HX_REQUEST": "true"}):
        html = client_rol("hr").get(reverse(ROYXAT), **htmx).content.decode()
        assert "Ombor" in html and "Bobur Aliyev" in html and "Ishlatilmoqda" in html
        assert "Javobgarsiz: 1" in html


def test_royxat_joylashuv_filial_cheklovi(foydalanuvchi, filial, filial_yarat):
    from django.test import Client

    boshqa = filial_yarat("B")
    av = av_yarat(filial, soni="1", qoldiq_filial=filial)
    from vositalar.tests.test_bayroqlar import qoldiq
    qoldiq(av, boshqa, "1")
    qator(av, filial, "1", mol=_xodim(filial, "Meniki"))
    qator(av, boshqa, "1", mol=_xodim(boshqa, "Begona"))
    c = Client()
    c.force_login(foydalanuvchi("hr", [filial]))
    html = c.get(reverse(ROYXAT)).content.decode()
    assert "Meniki" in html and "Begona" not in html


def test_mol_ismi_boyicha_qidiruv(client_rol, filial):
    bobur = av_yarat(filial)
    qator(bobur, filial, "1", mol=_xodim(filial, "Bobur Aliyev"))
    aziz = av_yarat(filial)
    qator(aziz, filial, "1", mol=_xodim(filial, "Aziz Karimov"))
    javob = client_rol("hr").get(reverse(ROYXAT), {"mol_ism": "bobur"})
    assert {a.pk for a in javob.context["sahifa"]} == {bobur.pk}
    html = client_rol("hr").get(reverse(ROYXAT)).content.decode()
    assert 'name="mol_ism"' in html and '<datalist id="mol_royxat">' in html


def test_bosh_hr_faqat_ozi_ishlaydigan_bayroqlar(client_rol):
    hr = {b["kalit"] for b in client_rol("hr").get(reverse("panel:bosh")).context["bayroqlar"]}
    assert hr == {"molsiz", "ketgan_xodimda", "bolimsiz"}
    kalitlar = {b["kalit"] for b in client_rol("admin").get(reverse("panel:bosh")).context["bayroqlar"]}
    assert kalitlar == set(BAYROQLAR)
    rahbar = {b["kalit"] for b in client_rol("rahbar").get(reverse("panel:bosh")).context["bayroqlar"]}
    assert rahbar == set(BAYROQLAR) - {"chiqim_kutilmoqda"}


def test_mol_nazorati_qidiruv_va_filtrlar(client_rol, filial):
    bobur = _xodim(filial, "Bobur Aliyev")
    _xodim(filial, "Aziz Karimov")
    ketgan = _xodim(filial, "Ketgan Odam", ishdan_bushagan=True)
    qator(av_yarat(filial), filial, "1", mol=bobur)
    c = client_rol("hr")
    url = reverse("mol:xodimlar")
    assert [x.ism for x in c.get(url, {"q": "bobur"}).context["xodimlar"]] == ["Bobur Aliyev"]
    assert [x.ism for x in c.get(url, {"av_bor": "1"}).context["xodimlar"]] == ["Bobur Aliyev"]
    assert [x.pk for x in c.get(url, {"holat": "ketgan"}).context["xodimlar"]] == [ketgan.pk]
    assert ketgan.pk not in [x.pk for x in c.get(url, {"holat": "faol"}).context["xodimlar"]]
    assert c.get(url, {"page": "x", "holat": "?"}).status_code == 200


def test_mol_nazorati_sahifalash(client_rol, filial):
    for i in range(55):
        _xodim(filial, f"Xodim {i:02d}")
    c = client_rol("hr")
    birinchi = c.get(reverse("mol:xodimlar"))
    assert len(birinchi.context["xodimlar"]) == 50
    assert len(c.get(reverse("mol:xodimlar"), {"page": 2}).context["xodimlar"]) == 5
