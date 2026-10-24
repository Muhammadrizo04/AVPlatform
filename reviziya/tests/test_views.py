import io

import pytest
from django.test import Client
from django.urls import reverse
from openpyxl import load_workbook
from pypdf import PdfReader

from reviziya.models import Reviziya, ReviziyaQollash
from reviziya.servis import reviziya_och
from reviziya.solishtir import solishtir
from vositalar.models import Bolim, Holat, Taqsimot
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db

XLSX_TURI = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def fb(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def revizor(foydalanuvchi):
    return foydalanuvchi("revizor")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


def kirgan(user):
    c = Client()
    c.force_login(user)
    return c


def matn(javob) -> str:
    return "".join(sahifa.extract_text() for sahifa in PdfReader(io.BytesIO(javob.content)).pages)


@pytest.fixture
def ikki_topilmadi(fa, revizor, hisobchi):
    """`fa` filialida A bo'limida ikkita AV (har biri 1 dona, qoldiq summasi 100); qayd yo'q — ikkalasi «topilmadi»."""
    a = Bolim.objects.create(filial=fa, nomi="A xona")
    stol, stul = av_yarat(fa, inv="INV-STOL"), av_yarat(fa, inv="INV-STUL")
    qator(stol, fa, "1", bolim=a)
    qator(stul, fa, "1", bolim=a)
    rv = reviziya_och(fa, None, [revizor], [{"ism": "Karimov A.", "lavozim": "Rais"}], hisobchi)
    return rv, stol, stul


def test_yangi_reviziya_formasi(fa, revizor, hisobchi, foydalanuvchi):
    bolim = Bolim.objects.create(filial=fa, nomi="Ombor")
    c = kirgan(hisobchi)
    assert c.get(reverse("reviziya:yangi")).status_code == 200
    forma = {
        "filial": fa.pk, "bolim": bolim.pk, "revizorlar": [revizor.pk], "izoh": "Yillik",
        "komissiya_ism": ["Karimov A.", "", "Valiyev B."], "komissiya_lavozim": ["Rais", "", ""],
    }

    r = c.post(reverse("reviziya:yangi"), forma)

    rv = Reviziya.objects.get()
    assert r.status_code == 302 and r["Location"] == reverse("reviziya:sahifa", args=[rv.pk])
    assert (rv.filial, rv.bolim, rv.izoh, rv.ochdi) == (fa, bolim, "Yillik", hisobchi)
    assert list(rv.revizorlar.all()) == [revizor]
    assert rv.komissiya == [
        {"xodim_id": None, "ism": "Karimov A.", "lavozim": "Rais", "rol": "azo"},
        {"xodim_id": None, "ism": "Valiyev B.", "lavozim": "", "rol": "azo"},
    ]

    assert kirgan(foydalanuvchi("hr")).post(reverse("reviziya:yangi"), forma).status_code == 403
    assert Reviziya.objects.count() == 1


def test_yangi_reviziya_xatolari(fa, fb, revizor, hisobchi, foydalanuvchi):
    c = kirgan(hisobchi)
    begona_bolim = Bolim.objects.create(filial=fb, nomi="B ombor")
    r = c.post(reverse("reviziya:yangi"), {"filial": fa.pk, "bolim": begona_bolim.pk, "revizorlar": [revizor.pk]})
    assert r.status_code == 400
    r = c.post(reverse("reviziya:yangi"), {"filial": fa.pk})
    assert r.status_code == 400
    # boshqa filialga biriktirilgan revizor tanlanmaydi
    begona = foydalanuvchi("revizor", [fb])
    r = c.post(reverse("reviziya:yangi"), {"filial": fa.pk, "revizorlar": [begona.pk]})
    assert r.status_code == 400
    # ruxsat etilmagan filial
    cheklangan = kirgan(foydalanuvchi("hisobchi", [fa]))
    r = cheklangan.post(reverse("reviziya:yangi"), {"filial": fb.pk, "revizorlar": [revizor.pk]})
    assert r.status_code == 400
    assert not Reviziya.objects.exists()


def test_royxat_filial_cheklovi(fa, fb, revizor, hisobchi, foydalanuvchi):
    bizniki = reviziya_och(fa, None, [revizor], [], hisobchi)
    begona = reviziya_och(fb, None, [revizor], [], hisobchi)
    c = kirgan(foydalanuvchi("hisobchi", [fa]))

    html = c.get(reverse("reviziya:royxat")).content.decode()

    assert bizniki.nomi in html and begona.nomi not in html
    assert c.get(reverse("reviziya:sahifa", args=[bizniki.pk])).status_code == 200
    for nom in ("sahifa", "excel", "pdf"):
        assert c.get(reverse(f"reviziya:{nom}", args=[begona.pk])).status_code == 404
    for nom in ("yakunla", "bekor", "qolla", "yop"):
        assert c.post(reverse(f"reviziya:{nom}", args=[begona.pk])).status_code == 404
    begona.refresh_from_db()
    assert begona.holat == Reviziya.Holat.OCHIQ


def test_royxat_holat_filtri(fa, fb, revizor, hisobchi):
    ochiq = reviziya_och(fa, None, [revizor], [], hisobchi)
    bekor = reviziya_och(fb, None, [revizor], [], hisobchi)
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:bekor", args=[bekor.pk]), follow=True)  # xabar shu yerda ko'rsatiladi

    html = c.get(reverse("reviziya:royxat"), {"holat": "ochiq"}).content.decode()

    assert ochiq.nomi in html and bekor.nomi not in html


def test_yakunla_va_qolla_oqimi(ikki_topilmadi, hisobchi, foydalanuvchi):
    rv, stol, stul = ikki_topilmadi
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    # HR ko'radi, lekin boshqarolmaydi
    hr = kirgan(foydalanuvchi("hr"))
    assert hr.get(sahifa).status_code == 200
    assert hr.post(reverse("reviziya:yakunla", args=[rv.pk])).status_code == 403

    assert c.post(reverse("reviziya:yakunla", args=[rv.pk])).status_code == 302
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN
    html = c.get(sahifa).content.decode()
    assert html.count('name="kalit"') == 2 and "qollangan-belgi" not in html

    kalit = next(q.kalit for q in solishtir(rv) if q.av_id == stol.pk)
    r = c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [kalit]}, follow=True)

    assert "1 ta qo&#x27;llandi, 0 ta xato" in r.content.decode()
    assert Taqsimot.objects.get(av=stol).holat == Holat.TOPILMADI
    assert Taqsimot.objects.get(av=stul).holat == Holat.ISHLATILMOQDA
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN  # hali qo'llanmagan qator bor
    html = c.get(sahifa).content.decode()
    assert html.count("qollangan-belgi") == 1 and html.count('name="kalit"') == 1

    # takror qo'llash — xato xabari bilan
    r = c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [kalit]}, follow=True)
    assert "0 ta qo&#x27;llandi, 1 ta xato" in r.content.decode()
    assert "allaqachon qo&#x27;llangan" in r.content.decode()

    assert c.post(reverse("reviziya:yop", args=[rv.pk])).status_code == 302
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.QOLLANGAN
    assert ReviziyaQollash.objects.filter(natija="ok").count() == 1


def test_hammasi_qollanganda_yopiladi(ikki_topilmadi, hisobchi):
    rv, _, _ = ikki_topilmadi
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    kalitlar = [q.kalit for q in solishtir(rv)]

    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": kalitlar})

    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.QOLLANGAN


def test_holat_xatosi_xabar_bilan(ikki_topilmadi, hisobchi):
    rv, _, _ = ikki_topilmadi
    c = kirgan(hisobchi)
    r = c.post(reverse("reviziya:yop", args=[rv.pk]), follow=True)  # ochiq reviziyani yopib bo'lmaydi
    assert "alert-danger" in r.content.decode()
    c.post(reverse("reviziya:bekor", args=[rv.pk]))
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.BEKOR


def test_guruh_filtri(ikki_topilmadi, hisobchi, fa):
    rv, stol, _ = ikki_topilmadi
    b = Bolim.objects.create(filial=fa, nomi="B xona")
    from reviziya.servis import qayd_qosh

    qayd_qosh(rv, Bolim.objects.get(nomi="A xona"), hisobchi, av=stol)
    qayd_qosh(rv, b, hisobchi, qr_matn="NOMALUM-QR")
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])

    html = c.get(sahifa, {"guruh": "ortiqcha"}).content.decode()
    assert "NOMALUM-QR" in html and stol.nomi not in html
    html = c.get(sahifa, {"guruh": "topildi"}).content.decode()
    assert stol.nomi in html and "NOMALUM-QR" not in html


def test_excel_va_pdf(ikki_topilmadi, hisobchi, foydalanuvchi):
    rv, stol, _ = ikki_topilmadi
    c = kirgan(hisobchi)

    r = c.get(reverse("reviziya:excel", args=[rv.pk]))
    assert r.status_code == 200 and r["Content-Type"] == XLSX_TURI
    varaq = load_workbook(io.BytesIO(r.content)).active
    satrlar = list(varaq.values)
    assert satrlar[0] == (
        "Guruh", "Inv. raqam", "AV", "Bo'lim", "Holat", "Kutilgan", "Topilgan", "Farq", "Nishon bo'lim", "Nishon holat",
    )
    assert ("Topilmadi", "INV-STOL", stol.nomi, "A xona", "Ishlatilmoqda", 1, 0, -1, None, None) in satrlar
    assert len(satrlar) == 3

    r = c.get(reverse("reviziya:pdf", args=[rv.pk]))
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    hisobchi_matni = matn(r).replace("\xa0", " ")
    assert rv.nomi in hisobchi_matni and "Karimov A." in hisobchi_matni
    assert "AV qiymati" in hisobchi_matni and "100,00" in hisobchi_matni and "200,00" in hisobchi_matni

    r = kirgan(foydalanuvchi("hr")).get(reverse("reviziya:pdf", args=[rv.pk]))
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    hr_matni = matn(r).replace("\xa0", " ")
    assert rv.nomi in hr_matni
    assert "AV qiymati" not in hr_matni and "100,00" not in hr_matni and "200,00" not in hr_matni


def test_menyu_bandi(client_rol):
    havola = reverse("reviziya:royxat")
    for rol in ("hisobchi", "hr", "rahbar"):
        r = client_rol(rol).get(reverse("panel:bosh"))
        assert r.status_code == 200 and f'href="{havola}"' in r.content.decode(), rol
        assert client_rol(rol).get(havola).status_code == 200, rol
    # revizor: panel «Reviziyalar» ochiladi, menyuda faqat shu bo'lim (boshqa panel bo'limlari unga yopiq)
    javob = client_rol("revizor").get(havola)
    html = javob.content.decode()
    assert javob.status_code == 200 and f'href="{havola}"' in html
    assert f'href="{reverse("vositalar:royxat")}"' not in html and f'href="{reverse("panel:bosh")}"' not in html


def test_bolimsiz_kochish_tanlanmaydi_va_yopilishga_toskinlik_qilmaydi(ikki_topilmadi, hisobchi):
    from reviziya.servis import qayd_qosh

    rv, stol, stul = ikki_topilmadi
    qayd_qosh(rv, None, hisobchi, av=stol)  # «Bo'limsiz» da topildi -> boshqa joyda, nishon yo'q
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    qatorlar = solishtir(rv)
    [bolimsiz] = [q for q in qatorlar if q.guruh == "boshqa_joyda"]
    [topilmadi] = [q for q in qatorlar if q.guruh == "topilmadi"]

    html = c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert f'value="{bolimsiz.kalit}"' not in html and f'value="{topilmadi.kalit}"' in html

    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [topilmadi.kalit]})

    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.QOLLANGAN


def test_ortiqcha_izohi_sahifa_excel_pdf(ikki_topilmadi, hisobchi, fb):
    from reviziya.servis import qayd_qosh

    rv, *_ = ikki_topilmadi
    arxiv = av_yarat(rv.filial, inv="INV-ARX", soni="0")
    qayd_qosh(rv, None, hisobchi, av=arxiv)
    qayd_qosh(rv, None, hisobchi, qr_matn="DS|B|9")
    c = kirgan(hisobchi)

    html = c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode().replace("&#x27;", "'")
    assert "Ortiqcha (arxivda)" in html and "Ortiqcha (boshqa filial)" in html and "Boshqa filial QR:" in html

    satrlar = list(load_workbook(io.BytesIO(c.get(reverse("reviziya:excel", args=[rv.pk])).content)).active.values)
    guruhlar = {s[0] for s in satrlar}
    assert {"Ortiqcha (arxivda)", "Ortiqcha (boshqa filial)"} <= guruhlar

    pdf_matni = matn(c.get(reverse("reviziya:pdf", args=[rv.pk])))
    assert "Ortiqcha (arxivda)" in pdf_matni and "Ortiqcha (boshqa filial)" in pdf_matni


def test_revizorlarni_ozgartirish(ikki_topilmadi, revizor, hisobchi, foydalanuvchi, fb):
    rv, *_ = ikki_topilmadi
    yangi = foydalanuvchi("revizor")
    url = reverse("reviziya:revizorlar", args=[rv.pk])
    c = kirgan(hisobchi)
    assert "O'zgartirish" in c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()

    assert c.post(url, {"revizorlar": [yangi.pk]}).status_code == 302
    assert list(rv.revizorlar.all()) == [yangi]

    # bo'sh ro'yxat va boshqa filial revizori — o'zgarmaydi
    c.post(url, {})
    c.post(url, {"revizorlar": [foydalanuvchi("revizor", [fb]).pk]})
    assert list(rv.revizorlar.all()) == [yangi]

    assert kirgan(foydalanuvchi("hr")).post(url, {"revizorlar": [revizor.pk]}).status_code == 403
    rv.holat = Reviziya.Holat.YAKUNLANGAN
    rv.save()
    c.post(url, {"revizorlar": [revizor.pk]})
    assert list(rv.revizorlar.all()) == [yangi]
    assert "O'zgartirish" not in c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()


def test_vedomost_va_royxat_saralash(ikki_topilmadi, revizor, hisobchi, fb):
    from reviziya.servis import qayd_qosh

    rv, stol, stul = ikki_topilmadi
    qayd_qosh(rv, Bolim.objects.get(nomi="A xona"), hisobchi, av=stul, soni=3)  # stul: farq +2 (ortiqcha)
    c = kirgan(hisobchi)
    url = reverse("reviziya:sahifa", args=[rv.pk])

    invlar = [s["q"].inv for s in c.get(url, {"tartib": "-inv"}).context["satrlar"]]
    assert invlar == sorted(invlar, reverse=True) and invlar[-1] == "INV-STOL"
    farqlar = [s["q"].farq for s in c.get(url, {"tartib": "farq"}).context["satrlar"]]
    assert farqlar == sorted(farqlar)
    html = c.get(url, {"tartib": "farq", "guruh": "topilmadi"}).content.decode()
    assert 'name="tartib" value="farq"' in html  # filtr formasi tartibni saqlaydi

    ikkinchi = reviziya_och(fb, None, [revizor], [], hisobchi)
    royxat = c.get(reverse("reviziya:royxat"), {"tartib": "raqam"}).context["sahifa"]
    assert [r.pk for r in royxat] == [rv.pk, ikkinchi.pk]
    assert [r.pk for r in c.get(reverse("reviziya:royxat")).context["sahifa"]] == [ikkinchi.pk, rv.pk]


def test_skanerlash_tugmasi(ikki_topilmadi, hisobchi, foydalanuvchi):
    rv, *_ = ikki_topilmadi
    sahifa_url, skan_url = reverse("reviziya:sahifa", args=[rv.pk]), reverse("reviziya:mobil_xonalar", args=[rv.pk])

    html = kirgan(hisobchi).get(sahifa_url).content.decode()
    assert f'href="{skan_url}"' in html
    assert f'href="{reverse("reviziya:mobil")}"' not in html  # menyuda alohida band yo'q

    assert skan_url not in kirgan(foydalanuvchi("hr")).get(sahifa_url).content.decode()

    rv.holat = Reviziya.Holat.YAKUNLANGAN
    rv.save()
    assert skan_url not in kirgan(hisobchi).get(sahifa_url).content.decode()


def test_qollangan_holat_yorligi_yopilgan():
    """«qollangan» holati foydalanuvchiga «Yopilgan» deb ko'rinadi (farqlarning bir qismi qo'llanmagan bo'lishi mumkin)."""
    from reviziya.models import Reviziya

    assert dict(Reviziya.Holat.choices)["qollangan"] == "Yopilgan"


def test_qollangan_farqlar_hisoblagichi_va_yopish_ogohlantirishi(ikki_topilmadi, hisobchi):
    """Sahifada «Qo'llangan farqlar: X / Y»; yopish tasdig'ida qo'llanmaganlar soni aytiladi."""
    rv, stol, _ = ikki_topilmadi
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    kalit = next(q.kalit for q in solishtir(rv) if q.av_id == stol.pk)
    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [kalit]})

    javob = c.get(sahifa)
    assert javob.context["farqlar"] == {"jami": 2, "qollangan": 1, "qolgan": 1}
    html = javob.content.decode()
    assert "Qo'llangan farqlar" in html and "1 / 2" in html
    assert "2 ta farqdan 1 tasi hali qo'llanmagan" in html and "data-tasdiq-xavfli" in html


def test_yopilganni_yakunlanganga_qaytarish(ikki_topilmadi, hisobchi, foydalanuvchi):
    rv, stol, stul = ikki_topilmadi
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    c.post(reverse("reviziya:yop", args=[rv.pk]))  # hech narsa qo'llanmasdan yopilgan
    qaytar = reverse("reviziya:qaytar", args=[rv.pk])
    assert 'action="%s"' % qaytar in c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert kirgan(foydalanuvchi("hr")).post(qaytar).status_code == 403

    assert c.post(qaytar).status_code == 302
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN and rv.qollangan_vaqt is None and rv.qolladi is None

    # endi farqlarni qo'llash mumkin
    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [q.kalit for q in solishtir(rv)]})
    assert Taqsimot.objects.get(av=stol).holat == Holat.TOPILMADI
    assert Taqsimot.objects.get(av=stul).holat == Holat.TOPILMADI
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.QOLLANGAN  # hammasi qo'llangach o'zi yopildi


def test_ochiq_reviziyani_qaytarib_bolmaydi(ikki_topilmadi, hisobchi):
    rv, _, _ = ikki_topilmadi
    r = kirgan(hisobchi).post(reverse("reviziya:qaytar", args=[rv.pk]), follow=True)
    assert "alert-danger" in r.content.decode()
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.OCHIQ


def test_qollash_eslatmasi_va_yopishqoq_panel(ikki_topilmadi, hisobchi):
    """Yakunlanganda tepada «N ta farq qo'llanmagan» eslatmasi (vedomostga havola), Qo'llash — yopishqoq panelda."""
    rv, _, _ = ikki_topilmadi
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])

    html = c.get(sahifa).content.decode()
    assert "qollash-eslatma" in html and "2 ta farq hali qo" in html and 'href="?guruh=farqlar#vedomost"' in html
    assert 'id="vedomost"' in html and 'class="amal-panel"' in html and "data-hammasini-tanla" in html

    filtrlangan = c.get(sahifa, {"guruh": "farqlar"}).context["satrlar"]
    assert len(filtrlangan) == 2

    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [q.kalit for q in solishtir(rv)]})
    assert "qollash-eslatma" not in c.get(sahifa).content.decode()  # hammasi qo'llandi, yopildi


def test_qollashni_bekor_qilish_tugmasi_va_view(ikki_topilmadi, hisobchi, foydalanuvchi):
    rv, stol, _ = ikki_topilmadi
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    kalit = next(q.kalit for q in solishtir(rv) if q.av_id == stol.pk)
    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": [kalit]})
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    bekor_url = reverse("reviziya:qolla_bekor", args=[rv.pk])

    html = c.get(sahifa).content.decode()
    assert f'formaction="{bekor_url}"' in html and 'name="bekor_kalit"' in html
    assert kirgan(foydalanuvchi("hr")).post(bekor_url, {"bekor_kalit": kalit}).status_code == 403

    r = c.post(bekor_url, {"bekor_kalit": kalit}, follow=True)
    assert "bekor qilindi" in r.content.decode()
    assert Taqsimot.objects.get(av=stol).holat == Holat.ISHLATILMOQDA
    assert c.get(sahifa).context["farqlar"]["qollangan"] == 0


def test_revizor_oz_filialida_boshqaradi(fa, fb, foydalanuvchi, hisobchi):
    """Revizor o'z filialidagi reviziyani yakunlaydi; boshqa filialdagisi unga ko'rinmaydi (404)."""
    revizor = foydalanuvchi("revizor", filiallar=[fa])
    o_zi = reviziya_och(fa, None, [revizor], [], hisobchi)
    begona = reviziya_och(fb, None, [foydalanuvchi("revizor", filiallar=[fb])], [], hisobchi)
    c = kirgan(revizor)
    assert c.post(reverse("reviziya:yakunla", args=[o_zi.pk])).status_code == 302
    o_zi.refresh_from_db()
    assert o_zi.holat == Reviziya.Holat.YAKUNLANGAN
    assert c.post(reverse("reviziya:yakunla", args=[begona.pk])).status_code == 404
    assert begona.nomi not in c.get(reverse("reviziya:royxat")).content.decode()


def test_ochiq_reviziyada_sahifadan_belgilash(ikki_topilmadi, hisobchi, foydalanuvchi):
    """Ochiq reviziya sahifasida qatorlarni belgilab, sonini kiritib «Joyida» — qayd qo'shiladi (skanerlashsiz)."""
    from reviziya.models import ReviziyaQayd

    rv, stol, stul = ikki_topilmadi
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    html = c.get(sahifa).content.decode()
    belgila = reverse("reviziya:belgila", args=[rv.pk])
    assert f'action="{belgila}"' in html and 'name="belgi"' in html and "data-hammasini-tanla" in html

    a = Bolim.objects.get(nomi="A xona")
    kalit = f"{stol.pk}:{a.pk}:ishlatilmoqda"
    r = c.post(belgila, {"belgi": [kalit], f"soni_{kalit}": "1", "keyingi": sahifa + "?guruh=kamomad"})
    assert r.status_code == 302 and r.url == sahifa + "?guruh=kamomad"
    qayd = ReviziyaQayd.objects.get(av=stol)
    assert (qayd.bolim, qayd.soni, qayd.holat, qayd.kim) == (a, 1, "ishlatilmoqda", hisobchi)
    assert not ReviziyaQayd.objects.filter(av=stul).exists()
    # noto'g'ri son — hech narsa qo'shilmaydi
    kalit2 = f"{stul.pk}:{a.pk}:ishlatilmoqda"
    r = c.post(belgila, {"belgi": [kalit2], f"soni_{kalit2}": "abc"}, follow=True)
    assert "alert-danger" in r.content.decode() and not ReviziyaQayd.objects.filter(av=stul).exists()
    # HR — huquq yo'q; yakunlangan — xato
    assert kirgan(foydalanuvchi("hr")).post(belgila, {"belgi": [kalit2]}).status_code == 403
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    r = c.post(belgila, {"belgi": [kalit2], f"soni_{kalit2}": "1"}, follow=True)
    assert "alert-danger" in r.content.decode() and not ReviziyaQayd.objects.filter(av=stul).exists()


def test_qollashni_belgilab_ommaviy_bekor_qilish(ikki_topilmadi, hisobchi):
    rv, stol, stul = ikki_topilmadi
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    kalitlar = [q.kalit for q in solishtir(rv)]
    c.post(reverse("reviziya:qolla", args=[rv.pk]), {"kalit": kalitlar})
    c.post(reverse("reviziya:qaytar", args=[rv.pk]))  # hammasi qo'llanib yopilgan edi
    html = c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert html.count('name="bekor_kalit"') == 2 and "data-bekor-tugma" in html

    r = c.post(reverse("reviziya:qolla_bekor", args=[rv.pk]), {"bekor_kalit": kalitlar}, follow=True)
    assert "2 ta bekor qilindi" in r.content.decode()
    assert {t.holat for t in Taqsimot.objects.filter(av__in=[stol, stul])} == {Holat.ISHLATILMOQDA}
