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


def test_akt_yangi_faqat_ruxsat_filial_qatorlari(foydalanuvchi, filial, filial_yarat, bobur, aziz):
    boshqa = filial_yarat("B")
    stol = av_yarat(filial, "2", "200", "1", "Stol")
    shkaf = av_yarat(boshqa, "2", "200", "2", "Shkaf")
    oziniki = qator(stol, filial, "2", bobur)
    begona = qator(shkaf, boshqa, "2", bobur)
    c = client_user(foydalanuvchi("hr", [filial]))

    javob = c.get(reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk})
    assert javob.status_code == 200
    assert [t.pk for t in javob.context["qatorlar"]] == [oziniki.pk]
    assert "Shkaf" not in javob.content.decode()

    javob = c.post(
        reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk, "qabul": aziz.pk, "tanlangan": [begona.pk]}
    )
    assert javob.status_code == 400
    assert not MolAkt.objects.exists()

    javob = c.post(
        reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk, "qabul": aziz.pk, "tanlangan": [oziniki.pk]}
    )
    assert javob.status_code == 302
    assert {q.filial_id for q in MolAkt.objects.get().qatorlar.all()} == {filial.pk}


def test_akt_yangi_boshqa_filial_qabul_qiluvchisi_rad(foydalanuvchi, filial, filial_yarat, bobur):
    boshqa = filial_yarat("B")
    begona = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Begona", filial=boshqa)
    q = qator(av_yarat(filial, "1", "100"), filial, "1", bobur)
    c = client_user(foydalanuvchi("hr", [filial]))

    javob = c.get(reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk})
    assert "Begona" not in {x.ism for x in javob.context["qabul_qiluvchilar"]}
    javob = c.post(reverse("mol:akt_yangi"), {"topshiruvchi": bobur.pk, "qabul": begona.pk, "tanlangan": [q.pk]})
    assert javob.status_code == 400
    assert not MolAkt.objects.exists()


@pytest.fixture
def pdf_konteksti(monkeypatch):
    """`akt_pdf` shablon kontekstlari (PDF baytlaridan qiymat o'qimaslik uchun)."""
    import mol.pdf

    olingan = []
    asl = mol.pdf.render_to_string

    def ushla(shablon, kontekst):
        olingan.append(kontekst)
        return asl(shablon, kontekst)

    monkeypatch.setattr(mol.pdf, "render_to_string", ushla)
    return olingan


def test_tasdiqlangan_akt_qiymati_ozgarmaydi(client_rol, filial, bobur, aziz, pdf_konteksti):
    av = av_yarat(filial, "3", "300")
    q = qator(av, filial, "3", bobur)
    c = client_rol("hr")
    akt = akt_yarat(bobur, aziz, [(q, SON("2"))], kim=foydalanuvchi_ol(c))

    # Qoralama — joriy 1C qiymati.
    assert c.get(reverse("mol:akt", args=[akt.pk])).context["jami_qiymat"] == SON("200")
    AVQoldiq.objects.filter(av=av).update(summa=SON("600"))
    assert c.get(reverse("mol:akt", args=[akt.pk])).context["jami_qiymat"] == SON("400")

    assert c.post(reverse("mol:akt_tasdiqla", args=[akt.pk])).status_code == 302
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.TASDIQLANGAN
    assert akt.qatorlar.get().dona_narxi == SON("200.00")

    def qiymatlar():
        sahifa = c.get(reverse("mol:akt", args=[akt.pk])).context
        assert c.get(reverse("mol:akt_pdf", args=[akt.pk])).status_code == 200
        return sahifa["jami_qiymat"], pdf_konteksti[-1]["jami"]

    assert qiymatlar() == (SON("400"), "400.00")
    AVQoldiq.objects.filter(av=av).update(summa=SON("900"))  # 1C summa o'zgardi
    assert qiymatlar() == (SON("400"), "400.00")
    AVQoldiq.objects.filter(av=av).update(soni=SON("0"), summa=SON("0"))  # AV arxivga tushdi
    assert qiymatlar() == (SON("400"), "400.00")


def foydalanuvchi_ol(client):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(pk=client.session["_auth_user_id"])


def test_xodimlar_sahifasida_yangi_akt_tugmasi(client_rol, filial):
    havola = f'href="{reverse("mol:akt_yangi")}"'
    for rol in ("hisobchi", "hr", "admin"):
        assert havola in client_rol(rol).get(reverse("mol:xodimlar")).content.decode()
    assert havola not in client_rol("rahbar").get(reverse("mol:xodimlar")).content.decode()


def test_akt_yangi_qator_oldindan_tanlangan(client_rol, filial):
    stol = av_yarat(filial, kod="1", nomi="Stol")
    stul = av_yarat(filial, kod="2", nomi="Stul")
    t_stol = qator(stol, filial, "6")
    qator(stul, filial, "3")
    javob = client_rol("hisobchi").get(reverse("mol:akt_yangi"), {"qator": t_stol.pk})
    assert javob.status_code == 200
    assert [t.pk for t in javob.context["qatorlar"]] == [t_stol.pk]
    assert f'name="tanlangan" value="{t_stol.pk}" aria-label="Tanlash" data-soni="soni_{t_stol.pk}" checked' in javob.content.decode()


@pytest.mark.parametrize("qiymat", ["abc", "²", "9" * 25, "999999"])
def test_akt_yangi_notogri_qator_parametri(client_rol, filial, qiymat):
    av = av_yarat(filial)
    qator(av, filial, "6")
    javob = client_rol("hisobchi").get(reverse("mol:akt_yangi"), {"qator": qiymat})
    assert javob.status_code == 200
    assert len(javob.context["qatorlar"]) == 1


def _soni_inputlari(html):
    import re
    return re.findall(r'<input[^>]*name="soni_(\d+)"[^>]*>', html), re.findall(r'<input[^>]*name="soni_\d+"[^>]*>', html)


def test_akt_yangi_soni_faqat_tanlangan_qatorda_yuboriladi(client_rol, filial):
    stol = av_yarat(filial, kod="1", nomi="Stol")
    t1 = qator(stol, filial, "6")
    t2 = qator(av_yarat(filial, kod="2", nomi="Stul"), filial, "3")
    html = client_rol("hisobchi").get(reverse("mol:akt_yangi")).content.decode()
    _, inputlar = _soni_inputlari(html)
    assert len(inputlar) == 2 and all("disabled" in i for i in inputlar)  # tanlanmagan — yuborilmaydi
    html = client_rol("hisobchi").get(reverse("mol:akt_yangi"), {"qator": t1.pk}).content.decode()
    _, inputlar = _soni_inputlari(html)
    assert len(inputlar) == 1 and "disabled" not in inputlar[0]
    assert f"soni_{t2.pk}" not in html


def test_akt_yangi_soni_yuborilmasa_toliq_qator(client_rol, filial, aziz):
    t = qator(av_yarat(filial), filial, "6")
    javob = client_rol("hisobchi").post(reverse("mol:akt_yangi"), {"topshiruvchi": "", "tanlangan": [t.pk], "qabul": aziz.pk})
    assert javob.status_code == 302
    assert MolAkt.objects.get().qatorlar.get().soni == SON("6")


def test_akt_yangi_qidiruv_va_filial_filtri(client_rol, filial, filial_yarat):
    b = filial_yarat("B")
    stol = qator(av_yarat(filial, kod="1", nomi="Stol"), filial, "1")
    stul = qator(av_yarat(filial, kod="2", nomi="Stul"), filial, "1")
    stul_b = qator(av_yarat(b, kod="3", nomi="Stul"), b, "1")
    c = client_rol("hisobchi")
    pklar = lambda **p: {t.pk for t in c.get(reverse("mol:akt_yangi"), p).context["qatorlar"]}
    assert pklar(q="stul") == {stul.pk, stul_b.pk}
    assert pklar(q="INV-1") == {stol.pk}
    assert pklar(q="stul", filial=b.pk) == {stul_b.pk}
    assert pklar(filial="²") == {stol.pk, stul.pk, stul_b.pk}


def test_akt_yangi_qatorlar_soni_cheklangan(client_rol, filial, monkeypatch):
    import mol.views
    monkeypatch.setattr(mol.views, "AKT_QATOR_CHEGARASI", 2)
    for i in range(3):
        qator(av_yarat(filial, kod=str(i + 1)), filial, "1")
    javob = client_rol("hisobchi").get(reverse("mol:akt_yangi"))
    assert len(javob.context["qatorlar"]) == 2
    assert "Filtrni toraytiring" in javob.content.decode()
