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
    for nom in ("yakunla", "bekor", "ochiqqa", "belgila"):
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


def test_holat_xatosi_xabar_bilan(ikki_topilmadi, hisobchi):
    rv, _, _ = ikki_topilmadi
    c = kirgan(hisobchi)
    r = c.post(reverse("reviziya:ochiqqa", args=[rv.pk]), follow=True)  # ochiq reviziyani qaytarib bo'lmaydi
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
        r = client_rol(rol).get(reverse("panel:bosh"), follow=True)
        assert r.status_code == 200 and f'href="{havola}"' in r.content.decode(), rol
        assert client_rol(rol).get(havola).status_code == 200, rol
    # revizor: panel «Reviziyalar» ochiladi, menyuda faqat shu bo'lim (boshqa panel bo'limlari unga yopiq)
    javob = client_rol("revizor").get(havola)
    html = javob.content.decode()
    assert javob.status_code == 200 and f'href="{havola}"' in html
    assert f'href="{reverse("vositalar:royxat")}"' not in html and f'href="{reverse("panel:bosh")}"' not in html


def test_bolimsiz_kochish_yozilmaydi_va_xalaqit_bermaydi(ikki_topilmadi, hisobchi):
    from reviziya.servis import qayd_qosh

    rv, stol, stul = ikki_topilmadi
    qayd_qosh(rv, None, hisobchi, av=stol)  # «Bo'limsiz» da topildi -> boshqa joyda, nishon yo'q
    c = kirgan(hisobchi)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    qatorlar = solishtir(rv)
    [bolimsiz] = [q for q in qatorlar if q.guruh == "boshqa_joyda"]
    [topilmadi] = [q for q in qatorlar if q.guruh == "topilmadi"]

    # «Bo'limsiz» ga ko'chish yozilmaydi (farq hisobiga kirmaydi), topilmadi — yoziladi
    jurnal = set(rv.qollashlar.values_list("kalit", "natija"))
    assert jurnal == {(topilmadi.kalit, "ok")}
    javob = c.get(reverse("reviziya:sahifa", args=[rv.pk]))
    assert javob.context["farqlar"] == {"jami": 1, "yozilgan": 1, "yozilmagan": 0, "eski": 0}


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


def test_yakunlash_farqlarni_avga_yozadi_va_ochiqqa_qaytaradi(ikki_topilmadi, hisobchi, foydalanuvchi):
    """Oddiy oqim: Yakunlash — farqlar AV'larga yoziladi; «Ochiqqa qaytarish» — o'zgarishlar orqaga qaytadi."""
    rv, stol, stul = ikki_topilmadi
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    hr = kirgan(foydalanuvchi("hr"))
    assert hr.get(sahifa).status_code == 200
    assert hr.post(reverse("reviziya:yakunla", args=[rv.pk])).status_code == 403

    html = c.get(sahifa).content.decode()
    assert "2 ta farq (topilmagan — «Topilmadi»" in html  # yakunlash tasdig'ida
    r = c.post(reverse("reviziya:yakunla", args=[rv.pk]), follow=True)
    assert "yakunlandi: 2 ta farq AV taqsimotiga yozildi" in r.content.decode()
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN
    assert {t.holat for t in Taqsimot.objects.filter(av__in=[stol, stul])} == {Holat.TOPILMADI}

    javob = c.get(sahifa)
    html = javob.content.decode()
    assert javob.context["farqlar"] == {"jami": 2, "yozilgan": 2, "yozilmagan": 0, "eski": 0}
    assert html.count("yozildi-belgi") == 2 and "Ochiqqa qaytarish" in html
    for eski in ("reviziya:qolla", "Qo&#x27;llash", "Yopish</button>"):
        assert eski not in html

    r = c.post(reverse("reviziya:ochiqqa", args=[rv.pk]), follow=True)
    assert "AV o&#x27;zgarishlari orqaga qaytarildi" in r.content.decode()
    rv.refresh_from_db()
    assert (rv.holat, rv.yakunlangan_vaqt) == (Reviziya.Holat.OCHIQ, None)
    assert {t.holat for t in Taqsimot.objects.filter(av__in=[stol, stul])} == {Holat.ISHLATILMOQDA}
    assert 'name="belgi"' in c.get(sahifa).content.decode()  # endi sahifadan son kiritish mumkin


def test_yozilmagan_farq_sababi_bilan(ikki_topilmadi, hisobchi, fa):
    from vositalar.amallar import kochir

    rv, stol, _ = ikki_topilmadi
    b = Bolim.objects.create(filial=fa, nomi="B xona")
    kochir(Taqsimot.objects.get(av=stol), "1", b, hisobchi)  # suratdan keyin ko'chirildi — yozib bo'lmaydi
    c = kirgan(hisobchi)
    r = c.post(reverse("reviziya:yakunla", args=[rv.pk]), follow=True)
    assert "1 tasi yozilmadi" in r.content.decode()

    javob = c.get(reverse("reviziya:sahifa", args=[rv.pk]))
    html = javob.content.decode()
    assert javob.context["farqlar"] == {"jami": 2, "yozilgan": 1, "yozilmagan": 1, "eski": 0}
    assert "yozilmagan-eslatma" in html and "Taqsimot o&#x27;zgargan" in html


def test_farqsiz_va_eski_tartibdagi_yakunlangan(ikki_topilmadi, hisobchi):
    from reviziya.servis import qayd_qosh, yakunla

    rv, stol, stul = ikki_topilmadi
    a = Bolim.objects.get(nomi="A xona")
    c = kirgan(hisobchi)
    # eski tartib: yakunlangan, lekin farqlar yozilmagan — qatorda yo'riqnoma
    yakunla(rv, hisobchi)
    html = c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert "2 tasi yozilmadi" in html and "Eski tartibda yakunlangan" in html and "reviziya eski tartibda yakunlangan" in html

    c.post(reverse("reviziya:ochiqqa", args=[rv.pk]))
    qayd_qosh(rv, a, hisobchi, av=stol)
    qayd_qosh(rv, a, hisobchi, av=stul)
    c.post(reverse("reviziya:yakunla", args=[rv.pk]))
    html = c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert "farq yo&#x27;q — hamma AV joyida" in html or "farq yo'q — hamma AV joyida" in html


def test_ochiq_reviziyada_belgini_olib_tashlash(ikki_topilmadi, hisobchi, fa, foydalanuvchi):
    """«Joyida» ning teskarisi: topilgan qatorni belgilab, belgisini olib tashlash — qayddan shu qator soni ayiriladi."""
    from reviziya.models import ReviziyaQayd
    from reviziya.servis import qayd_qosh

    rv, stol, stul = ikki_topilmadi
    a = Bolim.objects.get(nomi="A xona")
    b = Bolim.objects.create(filial=fa, nomi="B xona")
    qayd_qosh(rv, a, hisobchi, av=stol)  # topildi
    qayd_qosh(rv, b, hisobchi, av=stul, soni=__import__("decimal").Decimal("2"))  # boshqa joyda 1 + ortiqcha 1
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    olib_url = reverse("reviziya:belgini_ol", args=[rv.pk])
    qatorlar = {q.guruh: q for q in solishtir(rv)}

    html = c.get(sahifa).content.decode()
    assert f'formaction="{olib_url}"' in html and html.count('name="olib"') == 3
    assert 'href="?guruh=topildi#vedomost" data-topilganlar' in html  # topilganlarga tez o'tish

    r = c.post(olib_url, {"olib": [qatorlar["topildi"].kalit, qatorlar["boshqa_joyda"].kalit]}, follow=True)
    assert "2 ta qatorning belgisi olib tashlandi" in r.content.decode()
    assert not ReviziyaQayd.objects.filter(av=stol).exists()
    assert ReviziyaQayd.objects.get(av=stul).soni == 1  # ortiqcha qismi qoldi
    assert {q.guruh for q in solishtir(rv)} == {"topilmadi", "boshqa_joyda"}  # qolgan 1 dona yana moslashadi

    assert kirgan(foydalanuvchi("hr")).post(olib_url, {"olib": ["x"]}).status_code == 403
    r = c.post(olib_url, {"olib": ["mavjud-emas"]}, follow=True)
    assert "alert-danger" in r.content.decode()


def test_skanerlash_tugmasi_boshlash_nomida(ikki_topilmadi, hisobchi):
    rv, *_ = ikki_topilmadi
    html = kirgan(hisobchi).get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert "</i>Boshlash</a>" in html and "</i>Skanerlash</a>" not in html


def test_belgilash_soni_katak_qiymatida(ikki_topilmadi, hisobchi):
    """Ko'p qatorli vedomost: son katak qiymatida keladi («belgi=soni»), alohida soni_* maydonlari shart emas
    (aks holda 500+ qatorda DATA_UPLOAD_MAX_NUMBER_FIELDS dan oshadi)."""
    from reviziya.models import ReviziyaQayd

    rv, stol, _ = ikki_topilmadi
    a = Bolim.objects.get(nomi="A xona")
    c = kirgan(hisobchi)
    r = c.post(reverse("reviziya:belgila", args=[rv.pk]), {"belgi": [f"{stol.pk}:{a.pk}:ishlatilmoqda=1"]})
    assert r.status_code == 302
    assert ReviziyaQayd.objects.get(av=stol).soni == 1
    html = c.get(reverse("reviziya:sahifa", args=[rv.pk])).content.decode()
    assert "data-soni-jamla" in html


def test_panelda_av_qidirib_qoshish(ikki_topilmadi, hisobchi, fa, filial_yarat, foydalanuvchi):
    """Ochiq reviziya sahifasida AV qidirish: shu filialdan yoki boshqa filialdan (aniq inv.) — topildi deb qo'shish."""
    from reviziya.models import ReviziyaQayd

    rv, stol, _ = ikki_topilmadi
    a = Bolim.objects.get(nomi="A xona")
    begona = av_yarat(filial_yarat("02", "Showroom"), inv="INV_100652")
    c = kirgan(hisobchi)
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])
    qidir = reverse("reviziya:qidir", args=[rv.pk])
    qosh = reverse("reviziya:qayd_qosh", args=[rv.pk])
    assert f'hx-get="{qidir}"' in c.get(sahifa).content.decode()

    html = c.get(qidir, {"q": "INV_100652"}).content.decode()
    assert begona.nomi in html and "Showroom" in html and 'value="DS|02|INV_100652"' in html
    av_yarat(filial_yarat("03", "Yaypan"), inv="INV_100652-2")
    html = c.get(qidir, {"q": "00652"}).content.decode()  # inv. raqam qismi (kamida 5 belgi) — ikkalasi
    assert 'value="DS|02|INV_100652"' in html and 'value="DS|03|INV_100652-2"' in html
    r = c.post(qosh, {"qr": "DS|02|INV_100652", "bolim": a.pk, "soni": "1", "keyingi": sahifa}, follow=True)
    assert "qo&#x27;shildi" in r.content.decode()
    q = ReviziyaQayd.objects.get(av__isnull=True)
    assert (q.qr_matn, q.bolim, q.soni) == ("DS|02|INV_100652", a, 1)
    assert [x.izoh for x in solishtir(rv) if x.guruh == "ortiqcha"] == ["boshqa filial"]
    assert "boshqa filial: Showroom" in c.get(sahifa).content.decode()  # vedomostda AV nomi va filiali

    html = c.get(qidir, {"q": "INV-STOL"}).content.decode()  # shu filialdagi AV
    assert stol.nomi in html and f'name="av" value="{stol.pk}"' in html
    c.post(qosh, {"av": stol.pk, "bolim": a.pk, "soni": "1"})
    assert ReviziyaQayd.objects.get(av=stol).soni == 1

    # noma'lum QR / begona AV id rad etiladi; HR — 403
    r = c.post(qosh, {"qr": "DS|99|YOQ", "bolim": a.pk, "soni": "1"}, follow=True)
    assert "alert-danger" in r.content.decode()
    r = c.post(qosh, {"av": begona.pk, "bolim": a.pk, "soni": "1"}, follow=True)
    assert "alert-danger" in r.content.decode()
    assert kirgan(foydalanuvchi("hr")).get(qidir, {"q": "x"}).status_code == 403


def test_faqat_oz_reviziyasi_sozlamasi(ikki_topilmadi, revizor, hisobchi, foydalanuvchi):
    """«Faqat o'z reviziyasi»: o'chiq — boshqa hisobchi ham o'zgartiradi; yoqilgan — faqat ochgan kishi, revizorlari
    va admin; boshqalar sahifani ko'radi, lekin amal tugmalari yo'q va so'rovlar 403; mobil ro'yxatida ham yo'q."""
    from vositalar.models import Sozlama

    rv, stol, _ = ikki_topilmadi
    boshqa_hisobchi, boshqa_revizor = kirgan(foydalanuvchi("hisobchi")), kirgan(foydalanuvchi("revizor"))
    yakunla = reverse("reviziya:yakunla", args=[rv.pk])
    belgila = reverse("reviziya:belgila", args=[rv.pk])
    sahifa = reverse("reviziya:sahifa", args=[rv.pk])

    # o'chiq (standart): boshqa hisobchi ham belgilay oladi, boshqa revizor mobil ro'yxatda ko'rmaydi (revizori emas)
    assert boshqa_hisobchi.get(sahifa).context["boshqarish"] is True
    assert rv.nomi in boshqa_revizor.get(reverse("reviziya:mobil")).content.decode()  # boshqaruvchi — barchasi

    Sozlama.objects.filter(pk=Sozlama.PK).update(reviziya_faqat_ozimniki=True)
    javob = boshqa_hisobchi.get(sahifa)
    assert javob.status_code == 200 and javob.context["boshqarish"] is False and not javob.context["skanerlay_oladi"]
    assert boshqa_hisobchi.post(yakunla).status_code == 403
    assert boshqa_hisobchi.post(belgila, {"belgi": "x"}).status_code == 403
    assert boshqa_hisobchi.post(reverse("reviziya:bekor", args=[rv.pk])).status_code == 403
    assert rv.nomi not in boshqa_revizor.get(reverse("reviziya:mobil")).content.decode()
    assert boshqa_revizor.get(reverse("reviziya:mobil_skan", args=[rv.pk])).status_code == 404
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.OCHIQ

    # biriktirilgan revizor skanerlaydi, ochgan hisobchi va admin yakunlay oladi
    assert rv.nomi in kirgan(revizor).get(reverse("reviziya:mobil")).content.decode()
    assert kirgan(hisobchi).get(sahifa).context["boshqarish"] is True
    assert kirgan(foydalanuvchi("admin")).post(yakunla).status_code == 302
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN


def test_umumiy_sozlamada_reviziya_katakchasi(client_rol):
    from vositalar.models import Sozlama

    admin = client_rol("admin")
    html = admin.get(reverse("panel:umumiy")).content.decode()
    assert 'name="reviziya_faqat_ozimniki"' in html
    assert admin.post(reverse("panel:umumiy"), {"kompaniya_nomi": "X", "reviziya_faqat_ozimniki": "on"}).status_code == 302
    assert Sozlama.ol().reviziya_faqat_ozimniki is True
    admin.post(reverse("panel:umumiy"), {"kompaniya_nomi": "X"})
    assert Sozlama.ol().reviziya_faqat_ozimniki is False
