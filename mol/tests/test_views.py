import uuid
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from mol.models import MolAkt
from mol.servis import akt_yarat
from onec.models import AV, AVQoldiq, Xodim
from vositalar.models import Holat, Taqsimot

SON = Decimal


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def bobur(filial):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Bobur", filial=filial)


@pytest.fixture
def aziz(filial):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Aziz", filial=filial)


def av_yarat(filial, soni="6", summa="600", kod="1", nomi="Stol"):
    av = AV.objects.create(ref_1c=uuid.uuid4(), kod=kod, nomi=nomi, inv_raqam=f"INV-{kod}")
    AVQoldiq.objects.create(av=av, filial=filial, soni=SON(soni), summa=SON(summa))
    return av


def qator(av, filial, soni, mol=None):
    return Taqsimot.objects.create(av=av, filial=filial, mol=mol, holat=Holat.ISHLATILMOQDA, soni=SON(soni))


def client_user(user):
    c = Client()
    c.force_login(user)
    return c


def test_xodimlar_soni_va_qiymati(client_rol, filial, bobur, aziz):
    stol = av_yarat(filial, "6", "600", "1", "Stol")
    stul = av_yarat(filial, "2", "50", "2", "Stul")
    qator(stol, filial, "4", bobur)
    qator(stol, filial, "2", aziz)
    qator(stul, filial, "2", bobur)
    javob = client_rol("hr").get(reverse("mol:xodimlar"))
    assert javob.status_code == 200
    satrlar = {x.ism: x for x in javob.context["xodimlar"]}
    assert satrlar["Bobur"].av_soni == SON("6")
    assert satrlar["Bobur"].qiymat == SON("450")  # 4*100 + 2*25
    assert satrlar["Aziz"].av_soni == SON("2")
    assert satrlar["Aziz"].qiymat == SON("200")


def test_xodimlar_filial_cheklovi(foydalanuvchi, filial, filial_yarat, bobur):
    boshqa = filial_yarat("B")
    av = av_yarat(filial, "3", "300")
    av2 = av_yarat(boshqa, "2", "400", "2", "Boshqa")
    qator(av, filial, "1", bobur)
    qator(av2, boshqa, "2", bobur)
    c = client_user(foydalanuvchi("hr", [boshqa]))
    javob = c.get(reverse("mol:xodimlar"))
    satrlar = {x.ism: x for x in javob.context["xodimlar"]}
    # Bobur ruxsat etilgan filialda ham ushlab turadi -> ko'rinadi; faqat ruxsat etilgan qatorlar hisoblanadi.
    assert satrlar["Bobur"].av_soni == SON("2")
    assert satrlar["Bobur"].qiymat == SON("400")
    assert c.get(reverse("mol:xodim", args=[bobur.pk])).status_code == 200


def test_xodim_sahifasi_korinmasa_404(foydalanuvchi, filial, filial_yarat, bobur):
    boshqa = filial_yarat("B")
    c = client_user(foydalanuvchi("hr", [boshqa]))
    assert c.get(reverse("mol:xodim", args=[bobur.pk])).status_code == 404


def test_xodimlar_sorovlar_soni_doimiy(client_rol, filial):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    av = av_yarat(filial, "30", "300")
    c = client_rol("hr")

    def sorovlar_soni():
        with CaptureQueriesContext(connection) as ctx:
            assert c.get(reverse("mol:xodimlar")).status_code == 200
        return len(ctx)

    def xodim_qosh(n):
        for i in range(n):
            x = Xodim.objects.create(ref_1c=uuid.uuid4(), ism=f"X{n}{i}", filial=filial)
            qator(av, filial, "1", x)

    xodim_qosh(2)
    oz = sorovlar_soni()
    xodim_qosh(8)
    assert sorovlar_soni() == oz


def test_ketganlar_royxati(client_rol, filial, bobur, aziz):
    av = av_yarat(filial, "5", "500")
    bobur.ishdan_bushagan = True
    bobur.save()
    qator(av, filial, "3", bobur)
    qator(av, filial, "2", aziz)
    javob = client_rol("hr").get(reverse("mol:ketganlar"))
    assert javob.status_code == 200
    html = javob.content.decode()
    assert "Bobur" in html
    assert "Aziz" not in html


def test_akt_yangi_faqat_topshiruvchi_qatorlari(client_rol, filial, bobur, aziz):
    stol = av_yarat(filial, "6", "600", "1", "Stol")
    stul = av_yarat(filial, "2", "50", "2", "Stul")
    lampa = av_yarat(filial, "1", "10", "3", "Lampa")
    qator(stol, filial, "4", bobur)
    qator(lampa, filial, "1", aziz)
    qator(stul, filial, "2")
    c = client_rol("hr")
    html = c.get(reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk}).content.decode()
    assert "Stol" in html
    assert "Lampa" not in html and "Stul" not in html
    html = c.get(reverse("mol:akt_yangi")).content.decode()
    assert "Stul" in html and "Stol" not in html


def test_akt_yangi_qabul_qiluvchi_faqat_faol(client_rol, filial, bobur):
    av = av_yarat(filial)
    qator(av, filial, "1", bobur)
    Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Ketgan", filial=filial, ishdan_bushagan=True)
    Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Nofaol", filial=filial, neaktiv=True)
    Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Yoqolgan", filial=filial, onec_da_yoq=True)
    Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Faol", filial=filial)
    javob = client_rol("hr").get(reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk})
    assert {x.ism for x in javob.context["qabul_qiluvchilar"]} == {"Faol"}


def test_akt_oqimi(client_rol, filial, bobur, aziz):
    av = av_yarat(filial, "6", "600")
    q = qator(av, filial, "6", bobur)
    c = client_rol("hr")
    javob = c.post(
        reverse("mol:akt_yangi"),
        {"topshiruvchi": bobur.pk, "qabul": aziz.pk, "tanlangan": [q.pk], f"soni_{q.pk}": "4", "izoh": "sinov"},
    )
    assert javob.status_code == 302
    akt = MolAkt.objects.get()
    assert akt.holat == MolAkt.Holat.QORALAMA
    sahifa = c.get(reverse("mol:akt", args=[akt.pk]))
    assert sahifa.status_code == 200
    assert "Tasdiqlash" in sahifa.content.decode()
    assert c.post(reverse("mol:akt_tasdiqla", args=[akt.pk])).status_code == 302
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.TASDIQLANGAN
    assert Taqsimot.objects.get(av=av, mol=aziz).soni == SON("4")
    assert Taqsimot.objects.get(av=av, mol=bobur).soni == SON("2")
    sahifa = c.get(reverse("mol:akt", args=[akt.pk]))
    assert "Tasdiqlash" not in sahifa.content.decode()
    pdf = c.get(reverse("mol:akt_pdf", args=[akt.pk]))
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    assert "inline" in pdf["Content-Disposition"] and akt.nomi in pdf["Content-Disposition"]
    assert pdf.content.startswith(b"%PDF")


def test_akt_yangi_notogri_id_rad_etiladi(client_rol, filial, bobur, aziz):
    av = av_yarat(filial, "3", "300", "1")
    boshqaniki = qator(av, filial, "3", aziz)
    qator(av, filial, "1", bobur)
    javob = client_rol("hr").post(
        reverse("mol:akt_yangi"),
        {"topshiruvchi": bobur.pk, "qabul": aziz.pk, "tanlangan": [boshqaniki.pk]},
    )
    assert javob.status_code == 400
    assert not MolAkt.objects.exists()


def test_tasdiqlash_xatosi_xabar(foydalanuvchi, filial, bobur, aziz):
    av = av_yarat(filial, "6", "600")
    q = qator(av, filial, "6", bobur)
    hr = foydalanuvchi("hr")
    akt = akt_yarat(bobur, aziz, [(q, SON("6"))], kim=hr)
    aziz.ishdan_bushagan = True
    aziz.save()
    javob = client_user(hr).post(reverse("mol:akt_tasdiqla", args=[akt.pk]), follow=True)
    assert javob.status_code == 200
    assert "faol xodim emas" in javob.content.decode()
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.QORALAMA


def test_akt_pdf_filial_cheklovi(foydalanuvchi, filial, filial_yarat, bobur, aziz):
    boshqa = filial_yarat("B")
    av = av_yarat(boshqa, "2", "200")
    q = qator(av, boshqa, "2", bobur)
    hr = foydalanuvchi("hr", [filial])
    akt = akt_yarat(bobur, aziz, [(q, SON("2"))], kim=hr)
    c = client_user(hr)
    assert c.get(reverse("mol:akt_pdf", args=[akt.pk])).status_code == 404
    assert c.get(reverse("mol:akt", args=[akt.pk])).status_code == 404
    assert c.post(reverse("mol:akt_tasdiqla", args=[akt.pk])).status_code == 404


def test_rahbar_akt_yaratolmaydi(client_rol, filial, bobur, aziz):
    c = client_rol("rahbar")
    assert c.get(reverse("mol:akt_yangi")).status_code == 403
    assert c.post(reverse("mol:akt_yangi"), {"qabul": aziz.pk}).status_code == 403
    assert c.post(reverse("mol:akt_tasdiqla", args=[1])).status_code == 403
    assert c.get(reverse("mol:xodimlar")).status_code == 200


def test_hr_akt_yaratadi(client_rol, filial, bobur):
    av = av_yarat(filial)
    qator(av, filial, "1", bobur)
    assert client_rol("hr").get(reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk}).status_code == 200
