"""Filial ruxsati: «Hamma filial» — alohida belgi, hech biri belgilanmasa foydalanuvchi hech qaysi filialni ko'rmaydi."""
import importlib

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from hisoblar.models import Profil
from jurnal.models import Jurnal
from onec.models import AV, Filial
from reviziya.forms import _filiali_bor, _revizor_tanlovi
from vositalar.bayroqlar import av_lar
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db

User = get_user_model()
KUCHLI = "Kuchli-parol-7391"
SAHIFALAR = [
    "panel:bosh", "panel:dinamika", "vositalar:royxat", "vositalar:royxat_excel", "vositalar:bolimlar", "mol:xodimlar",
    "mol:ketganlar", "mol:akt_royxat", "mol:akt_yangi", "hisobotlar:tozalash", "hisobotlar:kesim",
    "hisobotlar:mol_qaydnoma", "hisobotlar:bolim_qaydnoma", "hisobotlar:muddat", "chiqimlar:royxat", "chiqimlar:tarix",
    "reviziya:royxat", "reviziya:yangi",
]


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("01")


@pytest.fixture
def admin(client_rol):
    return client_rol("admin")


def filialsiz(foydalanuvchi, rol="hisobchi"):
    u = foydalanuvchi(rol)
    Profil.objects.filter(user=u).update(hamma_filial=False)
    return User.objects.get(pk=u.pk)


def kirgan(u):
    c = Client()
    c.force_login(u)
    return c


def forma(**qoshimcha):
    return {"username": "yangi", "rol": "hisobchi", "parol": KUCHLI, **qoshimcha}


def test_filial_belgilanmasa_hech_narsa_korinmaydi(foydalanuvchi, filial):
    qator(av_yarat(filial), filial, "1")
    u = filialsiz(foydalanuvchi)

    assert ruxsat_filial_idlar(u) == set()
    assert not filial_bilan_chekla(Filial.objects.all(), u, "pk").exists()
    assert not av_lar(u).exists() and AV.objects.exists()


def test_hamma_filial_belgisi_cheklamaydi(foydalanuvchi, filial):
    u = foydalanuvchi("hisobchi")

    assert ruxsat_filial_idlar(u) is None
    assert filial in filial_bilan_chekla(Filial.objects.all(), u, "pk")


def test_belgi_filial_royxatidan_ustun(foydalanuvchi, filial, filial_yarat):
    u = foydalanuvchi("hisobchi", filiallar=[filial])
    Profil.objects.filter(user=u).update(hamma_filial=True)

    assert ruxsat_filial_idlar(User.objects.get(pk=u.pk)) is None


def test_tanlangan_filial_cheklaydi(foydalanuvchi, filial, filial_yarat):
    filial_yarat("02")

    assert ruxsat_filial_idlar(foydalanuvchi("hisobchi", filiallar=[filial])) == {filial.pk}


@pytest.mark.parametrize("rol", ["admin", "hisobchi", "hr", "rahbar"])
@pytest.mark.parametrize("sahifa", SAHIFALAR)
def test_filialsiz_foydalanuvchida_sahifalar_buzilmaydi(foydalanuvchi, filial, rol, sahifa):
    qator(av_yarat(filial), filial, "1")

    assert kirgan(filialsiz(foydalanuvchi, rol)).get(reverse(sahifa)).status_code in (200, 302, 403)


def test_filialsiz_revizor_mobil_sahifasi_ishlaydi(foydalanuvchi, filial):
    c = kirgan(filialsiz(foydalanuvchi, "revizor"))

    assert c.get(reverse("reviziya:mobil")).status_code == 200
    assert c.get(reverse("reviziya:mobil_yangi")).status_code == 200


def test_filialsiz_revizor_hech_qaysi_filialga_tanlanmaydi(foydalanuvchi, filial):
    revizor = filialsiz(foydalanuvchi, "revizor")
    hamma = foydalanuvchi("revizor")
    shu = foydalanuvchi("revizor", filiallar=[filial])
    so_rovchi = foydalanuvchi("hisobchi", filiallar=[filial])

    assert set(_revizor_tanlovi(so_rovchi)) >= {hamma, shu} and revizor not in _revizor_tanlovi(so_rovchi)
    assert not _filiali_bor(revizor, filial) and _filiali_bor(hamma, filial) and _filiali_bor(shu, filial)


def test_yangi_foydalanuvchi_filialsiz(admin):
    admin.post(reverse("panel:foydalanuvchilar"), forma())

    assert ruxsat_filial_idlar(User.objects.get(username="yangi")) == set()


def test_yangi_foydalanuvchi_hamma_filial(admin):
    admin.post(reverse("panel:foydalanuvchilar"), forma(hamma_filial="on"))

    assert ruxsat_filial_idlar(User.objects.get(username="yangi")) is None


def test_hamma_filial_tanlangan_royxatni_tozalaydi(admin, filial):
    admin.post(reverse("panel:foydalanuvchilar"), forma(hamma_filial="on", filiallar=[filial.pk]))

    profil = User.objects.get(username="yangi").profil
    assert profil.hamma_filial and not profil.filiallar.exists()


def test_tahrirda_belgi_olib_tashlansa_ruxsat_yopiladi(admin, foydalanuvchi):
    u = foydalanuvchi("hisobchi")
    url = reverse("panel:foydalanuvchi_tahrir", args=[u.pk])

    assert 'name="hamma_filial"' in (html := admin.get(url).content.decode()) and "checked" in html.split('name="hamma_filial"')[1][:80]
    admin.post(url, {"username": u.username, "rol": "hisobchi", "is_active": "on"})

    assert ruxsat_filial_idlar(User.objects.get(pk=u.pk)) == set()
    assert Jurnal.objects.filter(maydon="hamma_filial", yangi="False").exists()


def test_forma_tugmasi_va_yangi_izoh(admin):
    html = admin.get(reverse("panel:foydalanuvchilar")).content.decode()

    assert "Hamma filial" in html and "hech qaysi filialni ko" in html and "barcha filiallarga ruxsat" not in html
    assert html.count('name="hamma_filial"') == 1


def test_royxatda_holat_chiqadi(admin, foydalanuvchi):
    hamma, yoq = foydalanuvchi("hisobchi"), filialsiz(foydalanuvchi)

    html = admin.get(reverse("panel:foydalanuvchilar")).content.decode()

    assert html.split(hamma.username)[1].split("</tr>")[0].count("hammasi") == 1
    assert "yo&#x27;q" in html.split(yoq.username)[1].split("</tr>")[0] or "yo'q" in html.split(yoq.username)[1].split("</tr>")[0]


def test_migratsiya_mavjud_foydalanuvchi_kirishini_saqlaydi(foydalanuvchi, filial):
    bosh, cheklangan = filialsiz(foydalanuvchi), foydalanuvchi("hisobchi", filiallar=[filial])
    Profil.objects.filter(user=cheklangan).update(hamma_filial=False)

    importlib.import_module("hisoblar.migrations.0002_profil_hamma_filial").bosh_profillarga_hamma_filial(apps, None)

    assert Profil.objects.get(user=bosh).hamma_filial
    assert not Profil.objects.get(user=cheklangan).hamma_filial
