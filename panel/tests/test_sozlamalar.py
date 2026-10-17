import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from conftest import PAROL
from jurnal.models import Jurnal
from jurnal.yoz import yoz
from onec.client import OneCXato
from onec.models import AVTuri, SinxronJurnal
from onec.sinxron import SinxronBand
from vositalar.models import AVTuriSozlama, Sozlama, YorliqOlchami

pytestmark = pytest.mark.django_db
User = get_user_model()
KUCHLI = "Kuchli-parol-2026!"


@pytest.fixture
def admin_user(foydalanuvchi):
    return foydalanuvchi("admin")


@pytest.fixture
def client_admin(admin_user, client):
    client.force_login(admin_user)
    return client


class SoxtaClient:
    """Bo'sh, lekin to'g'ri 1C javoblari."""

    login = "soxta-login"
    parol = "soxta-parol-777"

    def spravochniklar(self):
        return {"tashkilotlar": [], "filiallar": [], "av_turlari": [], "xodimlar": []}

    def vositalar(self):
        return {"vositalar": [], "qoldiqlar": []}

    def harakatlar(self, dan, gacha):
        return []


class XatoClient(SoxtaClient):
    def spravochniklar(self):
        raise OneCXato("1C javob bermadi (60 s ichida): /spravochniklar")


# --- foydalanuvchilar ---

def test_foydalanuvchi_yaratish_rol_filial(client_admin, filial_yarat):
    a, b = filial_yarat("A"), filial_yarat("B")
    javob = client_admin.post(reverse("panel:foydalanuvchilar"), {
        "username": "yangi", "ism": "Ali Valiyev", "rol": "hisobchi", "filiallar": [a.pk, b.pk], "parol": KUCHLI,
    })
    assert javob.status_code == 302
    user = User.objects.get(username="yangi")
    assert user.profil.rol == "hisobchi" and user.first_name == "Ali Valiyev"
    assert set(user.profil.filiallar.all()) == {a, b}
    assert user.check_password(KUCHLI) and user.is_active
    assert Jurnal.objects.filter(obyekt_turi="auth.user", obyekt_id=str(user.pk)).exists()
    assert not Jurnal.objects.filter(yangi__contains="Kuchli-parol").exists()


def test_foydalanuvchi_zaif_parol_va_takror_nom(client_admin, admin_user):
    url = reverse("panel:foydalanuvchilar")
    javob = client_admin.post(url, {"username": "x1", "rol": "hr", "parol": "12345678"})
    assert javob.status_code == 200 and not User.objects.filter(username="x1").exists()
    javob = client_admin.post(url, {"username": "x1", "rol": "hr"})  # parolsiz
    assert javob.status_code == 200 and not User.objects.filter(username="x1").exists()
    javob = client_admin.post(url, {"username": admin_user.username, "rol": "hr", "parol": KUCHLI})
    assert javob.status_code == 200
    javob = client_admin.post(url, {"username": "x2", "rol": "yoq-rol", "parol": KUCHLI})
    assert javob.status_code == 200 and not User.objects.filter(username="x2").exists()


def test_foydalanuvchi_tahrir_parolsiz_va_faolsizlantirish(client_admin, foydalanuvchi):
    user = foydalanuvchi("hr")
    url = reverse("panel:foydalanuvchi_tahrir", args=[user.pk])
    javob = client_admin.post(url, {"username": user.username, "ism": "Yangi Ism", "rol": "rahbar"})
    assert javob.status_code == 302
    user.refresh_from_db()
    assert user.first_name == "Yangi Ism" and user.profil.rol == "rahbar" and not user.is_active
    assert user.check_password(PAROL)  # parol bo'sh -> o'zgarmadi
    client_admin.post(url, {"username": user.username, "rol": "rahbar", "is_active": "on", "parol": "Boshqa-parol-2026!"})
    user.refresh_from_db()
    assert user.is_active and user.check_password("Boshqa-parol-2026!")


def test_admin_ozini_ochira_olmaydi(client_admin, admin_user):
    url = reverse("panel:foydalanuvchi_tahrir", args=[admin_user.pk])
    assert client_admin.post(url, {"username": admin_user.username, "rol": "admin"}).status_code == 200  # faol emas
    assert client_admin.post(url, {"username": admin_user.username, "rol": "hr", "is_active": "on"}).status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.is_active and admin_user.profil.rol == "admin"


def test_foydalanuvchi_tahrir_notogri_pk(client_admin):
    assert client_admin.get(reverse("panel:foydalanuvchi_tahrir", args=[10**30])).status_code == 404
    assert client_admin.get(reverse("panel:foydalanuvchi_tahrir", args=[999999])).status_code == 404


# --- umumiy ---

def test_umumiy_sozlama(client_admin):
    javob = client_admin.post(reverse("panel:umumiy"), {"kompaniya_nomi": "Dream Style"})
    assert javob.status_code == 302
    assert Sozlama.ol().kompaniya_nomi == "Dream Style"
    assert Jurnal.objects.filter(obyekt_turi="vositalar.sozlama", maydon="kompaniya_nomi", yangi="Dream Style").exists()
    assert "Dream Style" in client_admin.get(reverse("panel:umumiy")).content.decode()


# --- yorliq o'lchamlari ---

def olcham_post(client, **kw):
    data = {"nomi": "Kichik", "eni_mm": "50", "boyi_mm": "25", "faol": "on"}
    data.update(kw)
    return client.post(reverse("panel:yorliq_olchamlari"), data)


def test_yorliq_olchami_qoshish(client_admin):
    assert olcham_post(client_admin).status_code == 302
    o = YorliqOlchami.objects.get(nomi="Kichik")
    assert (o.eni_mm, o.boyi_mm) == (Decimal("50"), Decimal("25"))
    soni = YorliqOlchami.objects.count()
    for kw in ({"eni_mm": "10"}, {"boyi_mm": "200"}, {"eni_mm": "abc"}, {"eni_mm": "19.9"}, {"boyi_mm": "14"},
               {"eni_mm": "NaN"}, {"eni_mm": "1e400"}, {"nomi": ""}):
        kw.setdefault("nomi", "Xato")
        assert olcham_post(client_admin, **kw).status_code == 200
    assert YorliqOlchami.objects.count() == soni
    assert olcham_post(client_admin, nomi="Chegara", eni_mm="120", boyi_mm="15").status_code == 302


def test_yorliq_standart_almashadi(client_admin):
    olcham_post(client_admin, nomi="A", standart="on")
    olcham_post(client_admin, nomi="B", standart="on")
    a, b = YorliqOlchami.objects.get(nomi="A"), YorliqOlchami.objects.get(nomi="B")
    assert not a.standart and b.standart
    url = reverse("panel:yorliq_olchami_tahrir", args=[a.pk])
    assert client_admin.post(url, {"nomi": "A", "eni_mm": "50", "boyi_mm": "25", "faol": "on", "standart": "on"}).status_code == 302
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.standart and not b.standart


def test_yorliq_standartni_nofaol_qilib_bolmaydi(client_admin):
    olcham_post(client_admin, nomi="A", standart="on")
    a = YorliqOlchami.objects.get(nomi="A")
    url = reverse("panel:yorliq_olchami_tahrir", args=[a.pk])
    assert client_admin.post(url, {"nomi": "A", "eni_mm": "50", "boyi_mm": "25", "standart": "on"}).status_code == 200
    assert client_admin.post(url, {"nomi": "A", "eni_mm": "50", "boyi_mm": "25"}).status_code == 200
    a.refresh_from_db()
    assert a.faol and a.standart
    olcham_post(client_admin, nomi="B")
    b = YorliqOlchami.objects.get(nomi="B")
    url_b = reverse("panel:yorliq_olchami_tahrir", args=[b.pk])
    assert client_admin.post(url_b, {"nomi": "B", "eni_mm": "50", "boyi_mm": "25"}).status_code == 302  # standart emas
    b.refresh_from_db()
    assert not b.faol


# --- AV turlari ---

def maydon_post(*qatorlar, muddat=""):
    """qatorlar: (kalit, nomi, tip, majburiy, tanlov)"""
    data = {"xizmat_muddati_oy": muddat, "maydon_kalit": [], "maydon_nomi": [], "maydon_tip": [],
            "maydon_majburiy": [], "maydon_tanlov": []}
    for kalit, nomi, tip, majb, tanlov in qatorlar:
        data["maydon_kalit"].append(kalit)
        data["maydon_nomi"].append(nomi)
        data["maydon_tip"].append(tip)
        data["maydon_majburiy"].append(majb)
        data["maydon_tanlov"].append(tanlov)
    return data


@pytest.fixture
def tur():
    return AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="Kompyuter")


def test_av_turi_maydonlari_saqlash(client_admin, tur):
    url = reverse("panel:av_turi_tahrir", args=[tur.pk])
    assert tur.nomi in client_admin.get(reverse("panel:av_turlari")).content.decode()
    javob = client_admin.post(url, maydon_post(
        ("seriya_raqami", "Seriya raqami", "matn", "ha", ""),
        ("rang", "Rang", "tanlov", "yoq", "qora, oq ,qora,"),
        ("", "", "matn", "yoq", ""),  # bo'sh qator tushirib qoldiriladi
        muddat="36",
    ))
    assert javob.status_code == 302
    s = AVTuriSozlama.objects.get(av_turi=tur)
    assert s.xizmat_muddati_oy == 36
    assert s.maydonlar == [
        {"kalit": "seriya_raqami", "nomi": "Seriya raqami", "tip": "matn", "majburiy": True, "tanlov_qiymatlari": []},
        {"kalit": "rang", "nomi": "Rang", "tip": "tanlov", "majburiy": False, "tanlov_qiymatlari": ["qora", "oq"]},
    ]
    assert Jurnal.objects.filter(obyekt_turi="vositalar.avturisozlama", obyekt_id=str(s.pk)).exists()
    assert client_admin.post(url, maydon_post()).status_code == 302  # muddat va maydonlarni bo'shatish
    s.refresh_from_db()
    assert s.xizmat_muddati_oy is None and s.maydonlar == []


@pytest.mark.parametrize("qatorlar,muddat", [
    ([("a", "A", "notogri", "yoq", "")], ""),
    ([("a", "A", "tanlov", "yoq", "")], ""),
    ([("a", "A", "tanlov", "yoq", " , ,")], ""),
    ([("Katta Harf", "A", "matn", "yoq", "")], ""),
    ([("a-b", "A", "matn", "yoq", "")], ""),
    ([("a\n", "A", "matn", "yoq", "")], ""),
    ([("", "Nomi bor", "matn", "yoq", "")], ""),
    ([("a", "A", "matn", "yoq", ""), ("a", "B", "son", "yoq", "")], ""),
    ([], "0"), ([], "-5"), ([], "abc"), ([], "99999999999999999999"),
])
def test_av_turi_notogri_maydon(client_admin, tur, qatorlar, muddat):
    javob = client_admin.post(reverse("panel:av_turi_tahrir", args=[tur.pk]), maydon_post(*qatorlar, muddat=muddat))
    assert javob.status_code == 200
    assert not AVTuriSozlama.objects.filter(av_turi=tur).exists()


# --- sinxron ---

def test_hozir_sinxronla(client_admin, monkeypatch):
    monkeypatch.setattr("panel.sozlamalar.client_yarat", lambda: SoxtaClient())
    javob = client_admin.post(reverse("panel:hozir_sinxronla"), follow=True)
    assert javob.redirect_chain[-1][0] == reverse("panel:ulanish")
    assert SinxronJurnal.objects.filter(natija="ok").count() == 1


def test_hozir_sinxronla_band(client_admin, monkeypatch):
    monkeypatch.setattr("panel.sozlamalar.client_yarat", lambda: SoxtaClient())

    def band(client):
        raise SinxronBand("band")

    monkeypatch.setattr("panel.sozlamalar.sinxronla", band)
    javob = client_admin.post(reverse("panel:hozir_sinxronla"), follow=True)
    assert "Sinxron hozir ishlayapti" in javob.content.decode()


def test_hozir_sinxronla_band_natijasi(client_admin, monkeypatch):
    monkeypatch.setattr("panel.sozlamalar.client_yarat", lambda: SoxtaClient())
    monkeypatch.setattr("panel.sozlamalar.sinxronla", lambda client: SinxronJurnal.objects.create(
        boshlandi=timezone.now(), natija="band"))
    javob = client_admin.post(reverse("panel:hozir_sinxronla"), follow=True)
    assert "Sinxron hozir ishlayapti" in javob.content.decode()


def test_hozir_sinxronla_xato(client_admin, monkeypatch):
    monkeypatch.setattr("panel.sozlamalar.client_yarat", lambda: XatoClient())
    javob = client_admin.post(reverse("panel:hozir_sinxronla"), follow=True)
    matn = javob.content.decode()
    assert "1C javob bermadi" in matn and "soxta-parol-777" not in matn
    assert SinxronJurnal.objects.get().natija == "xato"


def test_hozir_sinxronla_faqat_post(client_admin):
    assert client_admin.get(reverse("panel:hozir_sinxronla")).status_code == 405


def test_ulanish_sahifasi_parolni_korsatmaydi(client_admin, settings):
    settings.ONEC_URL = "http://1c.local/base/hs/av"
    settings.ONEC_LOGIN = "integratsiya"
    settings.ONEC_PAROL = "juda-maxfiy-parol-4242"
    SinxronJurnal.objects.create(boshlandi=timezone.now() - timedelta(minutes=9), natija="xato", xato_matni="x")
    SinxronJurnal.objects.create(boshlandi=timezone.now() - timedelta(minutes=4), natija="xato", xato_matni="y")
    matn = client_admin.get(reverse("panel:ulanish")).content.decode()
    assert "juda-maxfiy-parol-4242" not in matn and "maxfiy" not in matn
    assert "http://1c.local/base/hs/av" in matn and "integratsiya" in matn
    assert "Ketma-ket xatolar: 2" in matn


def test_ulanish_url_ichidagi_parol_yashiriladi(client_admin, settings):
    settings.ONEC_URL = "http://foy:sirli-kalit@1c.local/hs/av"
    matn = client_admin.get(reverse("panel:ulanish")).content.decode()
    assert "sirli-kalit" not in matn and "1c.local" in matn


def test_sinxron_jurnal_tartib_va_sahifalash(client_admin):
    hozir = timezone.now()
    for i in range(55):
        SinxronJurnal.objects.create(
            boshlandi=hozir - timedelta(minutes=i), natija="ok" if i else "xato", xato_matni="OXIRGI" if i == 0 else ""
        )
    url = reverse("panel:sinxron_jurnal")
    javob = client_admin.get(url)
    assert len(javob.context["sahifa"]) == 50 and javob.context["sahifa"][0].xato_matni == "OXIRGI"
    assert len(client_admin.get(url, {"page": "2"}).context["sahifa"]) == 5
    assert client_admin.get(url, {"page": "zzz"}).status_code == 200


# --- jurnal ---

def test_jurnal_filtrlari(client_admin, admin_user):
    u1, u2 = User.objects.create_user("bir"), User.objects.create_user("ikki")
    yoz(u1, u1, "nomi", "a", "b")
    yoz(u2, admin_user, "rol", "a", "b")
    eski = yoz(u1, u2, "izoh", "a", "b")
    Jurnal.objects.filter(pk=eski.pk).update(qachon=timezone.now() - timedelta(days=10))
    url = reverse("panel:jurnal")

    def royxat(**p):
        return list(client_admin.get(url, p).context["sahifa"])

    assert len(royxat()) == 3
    assert {j.kim_nomi for j in royxat(kim="bir")} == {"bir"}
    assert len(royxat(obyekt_turi="auth.user")) == 3
    assert len(royxat(obyekt_turi="yoq.model")) == 0
    bugun = timezone.localdate()
    assert len(royxat(dan=bugun.isoformat())) == 2
    assert len(royxat(gacha=(bugun - timedelta(days=5)).isoformat())) == 1
    assert len(royxat(dan=bugun.isoformat(), kim="ikki")) == 1


@pytest.mark.parametrize("params", [
    {"dan": "kecha"}, {"gacha": "2026-13-45"}, {"dan": "٢٠٢٦-٠١-٠١"}, {"page": "-1"},
    {"page": "99999999999999999999"}, {"obyekt_turi": "x" * 5000}, {"dan": "9999-12-31", "gacha": "0001-01-01"},
])
def test_jurnal_notogri_parametrlar(client_admin, params):
    assert client_admin.get(reverse("panel:jurnal"), params).status_code == 200


def test_jurnal_nul_bayt_400(client_admin):
    # NUL bayt umumiy middleware'da rad etiladi (PostgreSQL'ga yetib bormaydi).
    assert client_admin.get(reverse("panel:jurnal"), {"kim": "a\x00b"}).status_code == 400


def test_jurnal_sahifalash(client_admin):
    u = User.objects.create_user("p")
    for _ in range(51):
        yoz(u, u, "m", "a", "b")
    assert len(client_admin.get(reverse("panel:jurnal")).context["sahifa"]) == 50


# --- ruxsat ---

SAHIFALAR = ["foydalanuvchilar", "av_turlari", "umumiy", "yorliq_olchamlari", "ulanish", "sinxron_jurnal", "jurnal"]


@pytest.mark.parametrize("rol", ["hisobchi", "hr", "rahbar", "revizor"])
def test_hisobchi_sozlamalarga_403(client_rol, rol):
    c = client_rol(rol)
    for nom in SAHIFALAR:
        assert c.get(reverse(f"panel:{nom}")).status_code == 403, nom
    assert c.post(reverse("panel:hozir_sinxronla")).status_code == 403
    assert c.post(reverse("panel:umumiy"), {"kompaniya_nomi": "X"}).status_code == 403
    assert not Sozlama.objects.filter(kompaniya_nomi="X").exists()


def test_kirmagan_login_sahifasiga(client):
    assert client.get(reverse("panel:umumiy")).status_code == 302


def test_admin_hamma_sahifani_korsatadi(client_admin):
    for nom in SAHIFALAR:
        assert client_admin.get(reverse(f"panel:{nom}")).status_code == 200, nom


def test_menyuda_sozlamalar_faqat_adminga(client_admin, client_rol):
    url = reverse("panel:foydalanuvchilar")
    assert url in client_admin.get(reverse("panel:bosh")).content.decode()
    assert url not in client_rol("hisobchi").get(reverse("panel:bosh")).content.decode()
