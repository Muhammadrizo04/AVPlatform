import html

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse

from conftest import PAROL
from hisoblar.huquqlar import (
    HUQUQLAR,
    amal_kerak,
    filial_bilan_chekla,
    huquqi_bor,
    ruxsat_filial_idlar,
)
from hisoblar.models import Rol
from onec.models import Filial


def test_admin_hamma_amal(foydalanuvchi):
    admin = foydalanuvchi(Rol.ADMIN)
    assert set(HUQUQLAR) == {
        "korish", "av_tahrir", "taqsimot", "bolim_tahrir", "mol_akt",
        "yorliq", "tozalash", "hisobot", "sozlama", "sinxron",
    }
    for amal in HUQUQLAR:
        assert huquqi_bor(admin, amal) is True, amal


def test_hisobchi_amallari(foydalanuvchi):
    u = foydalanuvchi(Rol.HISOBCHI)
    for amal in ("av_tahrir", "taqsimot", "bolim_tahrir", "mol_akt", "yorliq", "tozalash", "hisobot", "korish"):
        assert huquqi_bor(u, amal) is True, amal
    for amal in ("sozlama", "sinxron"):
        assert huquqi_bor(u, amal) is False, amal


def test_hr_amallari(foydalanuvchi):
    u = foydalanuvchi(Rol.HR)
    for amal in ("mol_akt", "hisobot", "korish"):
        assert huquqi_bor(u, amal) is True, amal
    for amal in ("av_tahrir", "taqsimot", "yorliq"):
        assert huquqi_bor(u, amal) is False, amal


def test_rahbar_faqat_korish_va_hisobot(foydalanuvchi):
    u = foydalanuvchi(Rol.RAHBAR)
    for amal in HUQUQLAR:
        assert huquqi_bor(u, amal) is (amal in {"korish", "hisobot"}), amal


def test_revizor_va_notanish_amalda_huquq_yoq(foydalanuvchi):
    u = foydalanuvchi(Rol.REVIZOR)
    assert not any(huquqi_bor(u, amal) for amal in HUQUQLAR)
    assert huquqi_bor(foydalanuvchi(Rol.ADMIN), "mavjud_emas") is False
    assert huquqi_bor(AnonymousUser(), "korish") is False


def test_revizor_panelga_kirolmaydi(foydalanuvchi):
    u = foydalanuvchi(Rol.REVIZOR)
    client = Client()
    javob = client.post(reverse("hisoblar:kirish"), {"username": u.username, "password": PAROL})
    assert javob.status_code == 200
    assert "Panelga kirish huquqi yo'q" in html.unescape(javob.content.decode())
    assert "_auth_user_id" not in client.session


def test_hisobchi_kira_oladi_va_chiqadi(foydalanuvchi):
    u = foydalanuvchi(Rol.HISOBCHI)
    client = Client()
    javob = client.post(reverse("hisoblar:kirish"), {"username": u.username, "password": PAROL})
    assert javob.status_code == 302
    assert client.session["_auth_user_id"] == str(u.pk)
    assert client.get(reverse("bosh")).status_code == 200
    javob = client.post(reverse("hisoblar:chiqish"))
    assert javob.status_code == 302
    assert "_auth_user_id" not in client.session


def test_filial_cheklovi(foydalanuvchi, filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    cheklangan = foydalanuvchi(Rol.HISOBCHI, filiallar=[a])
    assert ruxsat_filial_idlar(cheklangan) == {a.pk}
    assert list(filial_bilan_chekla(Filial.objects.all(), cheklangan, "pk")) == [a]

    hammasi = foydalanuvchi(Rol.HISOBCHI)
    assert ruxsat_filial_idlar(hammasi) is None
    assert set(filial_bilan_chekla(Filial.objects.all(), hammasi, "pk")) == {a, b}


def test_amal_kerak_dekoratori(foydalanuvchi):
    @amal_kerak("sinxron")
    def view(request):
        return HttpResponse("ok")

    def chaqir(user):
        request = RequestFactory().get("/")
        request.user = user
        return view(request)

    assert chaqir(foydalanuvchi(Rol.ADMIN)).status_code == 200
    with pytest.raises(PermissionDenied):
        chaqir(foydalanuvchi(Rol.HISOBCHI))
    javob = chaqir(AnonymousUser())
    assert javob.status_code == 302 and javob.url.startswith(reverse("hisoblar:kirish"))


def test_5_xato_urinishdan_keyin_blok(foydalanuvchi):
    u = foydalanuvchi(Rol.HISOBCHI)
    client = Client()
    url = reverse("hisoblar:kirish")
    for _ in range(5):
        client.post(url, {"username": u.username, "password": "noto'g'ri"})
    javob = client.post(url, {"username": u.username, "password": PAROL})
    assert javob.status_code == 429
    assert "_auth_user_id" not in client.session
