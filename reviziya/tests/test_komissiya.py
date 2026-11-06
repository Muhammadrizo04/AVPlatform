"""Komissiya: 1C xodimlaridan tanlash, rais/a'zo, lavozimni eslab qolish, dalolatnomada МОЛlar."""
import io
import uuid

import pytest
from django.test import Client
from django.urls import reverse
from pypdf import PdfReader

from onec.models import Xodim
from reviziya.models import Reviziya, XodimLavozimi
from reviziya.servis import ReviziyaXato, reviziya_och
from vositalar.models import Bolim
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def revizor(foydalanuvchi):
    return foydalanuvchi("revizor")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


def xodim(ism, filial=None, **kw):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism=ism, filial=filial, **kw)


def kirgan(user):
    c = Client()
    c.force_login(user)
    return c


def test_servis_rais_birinchi_takror_va_lavozim(fa, revizor, hisobchi):
    karim, vali = xodim(" Karimov A.", fa), xodim("Valiyev B.", fa)
    rv = reviziya_och(fa, None, [revizor], [
        {"xodim_id": vali.pk, "ism": "Valiyev B.", "lavozim": "Omborchi", "rol": "azo"},
        {"xodim_id": karim.pk, "ism": "Karimov A.", "lavozim": "Bosh hisobchi", "rol": "rais"},
        {"xodim_id": vali.pk, "ism": "Valiyev B.", "lavozim": "", "rol": "azo"},  # takror — tashlanadi
        {"xodim_id": None, "ism": "Tashqi auditor", "lavozim": "", "rol": "noma'lum"},
        {"xodim_id": None, "ism": "  ", "lavozim": "bo'sh ism", "rol": "azo"},
    ], hisobchi)

    assert [(a["ism"], a["rol"]) for a in rv.komissiya] == [
        ("Karimov A.", "rais"), ("Valiyev B.", "azo"), ("Tashqi auditor", "azo"),
    ]
    assert dict(XodimLavozimi.objects.values_list("xodim_id", "lavozim")) == {
        karim.pk: "Bosh hisobchi", vali.pk: "Omborchi",
    }


def test_servis_ikki_rais_xato(fa, revizor, hisobchi):
    with pytest.raises(ReviziyaXato, match="raisi bitta"):
        reviziya_och(fa, None, [revizor], [
            {"ism": "A", "rol": "rais"}, {"ism": "B", "rol": "rais"},
        ], hisobchi)
    assert not Reviziya.objects.exists()


def test_xodim_qidiruvi(fa, filial_yarat, hisobchi, foydalanuvchi):
    xodim("Karimov Anvar", fa)
    xodim(" Karimov Zafar", fa)  # 1C'dagi boshidagi bo'shliq tartibni buzmaydi
    xodim("Karimova Dilnoza", fa, ishdan_bushagan=True)
    xodim("Karimov Begona", filial_yarat("B"))
    url = reverse("reviziya:komissiya_xodimlar")

    html = kirgan(hisobchi).get(url, {"q": "karim"}).content.decode()
    assert "Karimov Anvar" in html and "Karimov Begona" in html and "Dilnoza" not in html
    assert html.index("Karimov Anvar") < html.index("Karimov Begona") < html.index("Karimov Zafar")

    # filial cheklovi: faqat ruxsat etilgan filial xodimlari
    html = kirgan(foydalanuvchi("hisobchi", [fa])).get(url, {"q": "karim"}).content.decode()
    assert "Karimov Anvar" in html and "Begona" not in html

    assert kirgan(hisobchi).get(url).content.decode().strip() == ""
    assert kirgan(foydalanuvchi("hr")).get(url, {"q": "karim"}).status_code == 403


def test_qator_lavozimni_eslab_qoladi(fa, hisobchi):
    karim = xodim("Karimov A.", fa)
    XodimLavozimi.objects.create(xodim=karim, lavozim="Bosh hisobchi")
    c = kirgan(hisobchi)
    url = reverse("reviziya:komissiya_qator")

    html = c.get(url, {"xodim": karim.pk, "n": "0"}).content.decode()
    assert 'value="Bosh hisobchi"' in html and 'value="rais" selected' in html and 'value="{}"'.format(karim.pk) in html

    html = c.get(url, {"xodim": karim.pk, "n": "2"}).content.decode()
    assert 'value="azo" selected' in html

    html = c.get(url, {"ism": "Tashqi auditor", "n": "1"}).content.decode()
    assert 'name="komissiya_ism" value="Tashqi auditor"' in html and "1C ro'yxatida yo'q" in html

    begona = xodim("Ketgan", fa, ishdan_bushagan=True)
    assert c.get(url, {"xodim": begona.pk}).status_code == 404


def test_yangi_reviziya_xodim_komissiyasi(fa, filial_yarat, revizor, foydalanuvchi):
    karim = xodim(" Karimov A.", fa)
    begona = xodim("Begona", filial_yarat("B"))
    c = kirgan(foydalanuvchi("hisobchi", [fa]))

    r = c.post(reverse("reviziya:yangi"), {
        "filial": fa.pk, "revizorlar": [revizor.pk],
        "komissiya_xodim": [karim.pk, begona.pk, ""],
        # xodim ismi formadan emas, 1C'dan olinadi
        "komissiya_ism": ["Soxta ism", "Begona", "Tashqi auditor"],
        "komissiya_lavozim": ["Rais o'rinbosari", "", "Auditor"],
        "komissiya_rol": ["rais", "azo", "azo"],
    })

    assert r.status_code == 302
    rv = Reviziya.objects.get()
    assert rv.komissiya == [
        {"xodim_id": karim.pk, "ism": "Karimov A.", "lavozim": "Rais o'rinbosari", "rol": "rais"},
        {"xodim_id": None, "ism": "Tashqi auditor", "lavozim": "Auditor", "rol": "azo"},
    ]


def test_yangi_reviziya_ikki_rais_formada_qaytadi(fa, revizor, hisobchi):
    a, b = xodim("Aliyev", fa), xodim("Boboyev", fa)
    r = kirgan(hisobchi).post(reverse("reviziya:yangi"), {
        "filial": fa.pk, "revizorlar": [revizor.pk],
        "komissiya_xodim": [a.pk, b.pk], "komissiya_ism": ["", ""], "komissiya_lavozim": ["", ""],
        "komissiya_rol": ["rais", "rais"],
    })
    html = r.content.decode()
    assert r.status_code == 400 and "raisi bitta" in html and "Aliyev" in html and "Boboyev" in html
    assert not Reviziya.objects.exists()


def test_dalolatnomada_rais_azolar_va_mollar(fa, revizor, hisobchi):
    ombor = Bolim.objects.create(filial=fa, nomi="Ombor")
    mol = xodim("Mirzayev Mol", fa)
    qator(av_yarat(fa, inv="INV-1"), fa, "1", bolim=ombor, mol=mol)
    qator(av_yarat(fa, inv="INV-2"), fa, "1", bolim=ombor, mol=mol)
    rv = reviziya_och(fa, None, [revizor], [
        {"ism": "Raisov R.", "lavozim": "Direktor", "rol": "rais"}, {"ism": "Azoyev A.", "rol": "azo"},
    ], hisobchi)

    r = kirgan(hisobchi).get(reverse("reviziya:pdf", args=[rv.pk]))
    matn = "".join(s.extract_text() for s in PdfReader(io.BytesIO(r.content)).pages)
    assert "Komissiya raisi" in matn and "Raisov R." in matn and "Azoyev A." in matn
    assert "Moddiy javobgar shaxslar" in matn and matn.count("Mirzayev Mol") == 1
