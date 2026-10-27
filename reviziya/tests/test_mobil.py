import html
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from reviziya.models import ReviziyaQayd
from reviziya.servis import qayd_qosh, reviziya_och, yakunla
from vositalar.models import Bolim, Rasm
from vositalar.tests.test_bayroqlar import av_yarat, qator
from vositalar.tests.test_kartochka import rasm_baytlari, yuklama

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def fa(filial_yarat):
    return filial_yarat("07")


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
    return html.unescape(javob.content.decode())


@pytest.fixture
def muhit(fa, revizor, hisobchi):
    """`fa` filiali, «Kabinet» xonasida INV-1 (2 dona) va INV-2 (1 dona); revizor biriktirilgan ochiq reviziya."""
    xona = Bolim.objects.create(filial=fa, nomi="Kabinet")
    stol, stul = av_yarat(fa, inv="INV-1", soni="2"), av_yarat(fa, inv="INV-2")
    qator(stol, fa, "2", bolim=xona)
    qator(stul, fa, "1", bolim=xona)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    return rv, xona, stol, stul


def url(nom, *args, **params):
    manzil = reverse(f"reviziya:{nom}", args=args)
    if params:
        manzil += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return manzil


def saqla(c, rv, xona, **maydonlar):
    data = {"bolim": xona.pk if xona else 0, "soni": "1", "usul": "qidiruv", **maydonlar}
    return c.post(url("mobil_saqla", rv.pk), data)


def test_revizor_kirganda_mobilga(muhit, revizor):
    c = kirgan(revizor)
    javob = c.get("/")
    assert javob.status_code == 302 and javob.url == reverse("reviziya:mobil")
    assert c.get("/av/").status_code == 403
    royxat = c.get(reverse("reviziya:mobil"))
    assert royxat.status_code == 200 and muhit[0].nomi in matn(royxat)


def test_hisobchi_boshda_qoladi(muhit, hisobchi):
    assert kirgan(hisobchi).get("/").status_code == 200


def test_faqat_biriktirilgan(muhit, foydalanuvchi, hisobchi, fa, filial_yarat):
    rv, xona, *_ = muhit
    # revizor reviziyani o'z filiallarida boshqaradi: boshqa filialdagi revizor — 404
    begona = kirgan(foydalanuvchi("revizor", filiallar=[filial_yarat("99")]))
    assert begona.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 404
    assert begona.get(url("mobil_topish", rv.pk, q="INV-1")).status_code == 404
    assert saqla(begona, rv, xona, av=muhit[2].pk).status_code == 404
    assert rv.nomi not in matn(begona.get(reverse("reviziya:mobil")))
    # reviziya_boshqarish — biriktirilmagan bo'lsa ham kiradi; boshqa filialdagi hisobchi — 404
    assert kirgan(hisobchi).get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 200
    boshqa_hisobchi = kirgan(foydalanuvchi("hisobchi", filiallar=[filial_yarat("99")]))
    assert boshqa_hisobchi.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 404
    # HR — reviziya_otkazish yo'q
    assert kirgan(foydalanuvchi("hr")).get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 403
    yakunla(rv, hisobchi)
    c = kirgan(muhit[0].revizorlar.first())
    assert c.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 403
    assert saqla(c, rv, xona, av=muhit[2].pk).status_code == 403
    assert rv.nomi not in matn(c.get(reverse("reviziya:mobil")))


def test_xonalar(muhit, revizor):
    rv, xona, *_ = muhit
    javob = kirgan(revizor).get(url("mobil_xonalar", rv.pk))
    t = matn(javob)
    assert javob.status_code == 200 and "Kabinet" in t and "Bo'limsiz" in t and "0 / 3" in t


def test_skan_xonani_eslab_qoladi(muhit, revizor):
    rv, xona, *_ = muhit
    c = kirgan(revizor)
    assert c.get(url("mobil_skan", rv.pk)).status_code == 302  # xona tanlanmagan
    assert c.get(url("mobil_skan", rv.pk, bolim=xona.pk)).status_code == 200
    javob = c.get(url("mobil_skan", rv.pk))
    assert javob.status_code == 200 and "Kabinet" in matn(javob)
    assert c.get(url("mobil_skan", rv.pk, bolim=0)).status_code == 200
    assert c.get(url("mobil_skan", rv.pk, bolim=999999)).status_code == 404


def test_qidiruv_va_saqlash(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    c.get(url("mobil_skan", rv.pk, bolim=xona.pk))
    javob = c.get(url("mobil_topish", rv.pk, q="INV-1"))
    t = matn(javob)
    assert javob.status_code == 200 and stol.nomi in t and "Kutilgan: 2" in t and "guruh × 2" in t
    assert saqla(c, rv, xona, av=stol.pk).status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv, av=stol)
    assert qayd.soni == 1 and qayd.bolim == xona and qayd.usul == "qidiruv" and qayd.kim == revizor
    assert saqla(c, rv, xona, av=stol.pk).status_code == 200
    qayd.refresh_from_db()
    assert qayd.soni == 2 and ReviziyaQayd.objects.count() == 1
    # topilmagan qidiruv
    assert "Hech narsa topilmadi" in matn(c.get(url("mobil_topish", rv.pk, q="YOQ-999")))


def test_boshqa_filial_av_saqlanmaydi(muhit, revizor, filial_yarat):
    rv, xona, *_ = muhit
    begona_av = av_yarat(filial_yarat("55"), inv="INV-X")
    javob = saqla(kirgan(revizor), rv, xona, av=begona_av.pk)
    assert javob.status_code == 400 and not ReviziyaQayd.objects.exists()


def test_qr_orqali_topish(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    c.get(url("mobil_skan", rv.pk, bolim=xona.pk))
    javob = c.get(url("mobil_topish", rv.pk, qr="DS|07|INV-1"))
    assert javob.status_code == 200 and stol.nomi in matn(javob) and 'value="qr"' in matn(javob)
    javob = c.get(url("mobil_topish", rv.pk, qr="abc"))
    assert javob.status_code == 200 and "noma'lum yorliq" in matn(javob).lower()
    assert saqla(c, rv, xona, qr_matn="abc", usul="qr").status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv)
    assert qayd.av is None and qayd.qr_matn == "abc" and qayd.usul == "qr"


def test_uzun_qr_kesiladi(muhit, revizor):
    rv, xona, *_ = muhit
    c = kirgan(revizor)
    uzun = "DS|07|" + "Z" * 294  # 300 belgi
    javob = c.get(reverse("reviziya:mobil_topish", args=[rv.pk]), {"qr": uzun, "bolim": xona.pk})
    assert javob.status_code == 200 and "noma'lum yorliq" in matn(javob).lower()
    assert saqla(c, rv, xona, qr_matn=uzun, usul="qr").status_code == 200
    assert ReviziyaQayd.objects.get(reviziya=rv).qr_matn == uzun[:255]


def test_vergulli_son(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    assert saqla(c, rv, xona, av=stol.pk, soni="1,5").status_code == 200
    assert ReviziyaQayd.objects.get(reviziya=rv).soni == Decimal("1.5")
    for yomon in ("-1", "", "0", "abc", "1000000", "NaN"):
        javob = saqla(c, rv, xona, av=stol.pk, soni=yomon)
        assert javob.status_code == 400, yomon
        assert "son" in matn(javob).lower()
    assert ReviziyaQayd.objects.get(reviziya=rv).soni == Decimal("1.5")


def test_tuzatish(muhit, revizor, foydalanuvchi, filial_yarat):
    rv, xona, stol, _ = muhit
    qayd = qayd_qosh(rv, xona, revizor, av=stol)
    c = kirgan(revizor)
    assert c.post(url("mobil_tuzat", qayd.pk), {"soni": "3"}).status_code == 200
    qayd.refresh_from_db()
    assert qayd.soni == 3
    assert c.post(url("mobil_tuzat", qayd.pk), {"soni": "-2"}).status_code == 400
    ikkinchi = foydalanuvchi("revizor")
    rv.revizorlar.add(ikkinchi)
    # revizor reviziyani boshqaradi — boshqa revizor qaydini ham tuzata oladi; boshqa filialdagisi — 404
    assert kirgan(ikkinchi).post(url("mobil_tuzat", qayd.pk), {"soni": "3"}).status_code == 200
    assert kirgan(foydalanuvchi("revizor", filiallar=[filial_yarat("99")])).post(url("mobil_tuzat", qayd.pk), {"soni": "1"}).status_code == 404
    assert kirgan(foydalanuvchi("hr")).post(url("mobil_tuzat", qayd.pk), {"soni": "1"}).status_code == 403
    assert c.post(url("mobil_tuzat", qayd.pk), {"soni": "0"}).status_code == 200
    assert not ReviziyaQayd.objects.exists()


def test_http_da_kamera_izohi(muhit, revizor):
    rv, xona, *_ = muhit
    t = matn(kirgan(revizor).get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "Kamera faqat HTTPS'da ishlaydi — inv. raqamni kiriting" in t
    assert "data-xavfsiz" in t and "skan.js" in t


def test_qolganlar(muhit, revizor):
    rv, xona, stol, stul = muhit
    c = kirgan(revizor)
    t = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "INV-1" in t and "INV-2" in t
    qayd_qosh(rv, xona, revizor, av=stul)
    t = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    qolganlar = t[t.index('id="qolganlar"'):]
    assert "INV-1" in qolganlar and "INV-2" not in qolganlar


def test_rasm_bilan_saqlash(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    javob = saqla(c, rv, xona, av=stol.pk, izoh="Singan", rasm=yuklama(rasm_baytlari(format="PNG"), nom="r.png"))
    assert javob.status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv)
    assert qayd.rasm is not None and qayd.rasm in Rasm.objects.filter(av=stol) and qayd.izoh == "Singan"
    javob = saqla(c, rv, xona, av=stol.pk, rasm=yuklama(b"rasm emas"))
    assert javob.status_code == 400 and "JPEG yoki PNG" in matn(javob)
    qayd.refresh_from_db()
    assert qayd.soni == 1


def test_nul_bayt_500_bermaydi(muhit, revizor):
    """Middleware NUL baytli so'rovni 400 bilan to'xtatadi; view o'zi ham NUL'ni olib tashlaydi (himoya qatlami)."""
    from django.contrib.sessions.backends.db import SessionStore
    from django.test import RequestFactory

    from reviziya import mobil

    rv, xona, *_ = muhit
    c = kirgan(revizor)
    assert c.get(url("mobil_topish", rv.pk, qr="DS|%00|X", bolim=xona.pk)).status_code == 400

    nul = chr(0)
    rf = RequestFactory()

    def sorov(r):
        r.user, r.session = revizor, SessionStore()
        return r

    javob = mobil.topish(sorov(rf.get("/", {"qr": f"DS|{nul}|X", "bolim": xona.pk})), rv.pk)
    assert javob.status_code == 200 and "noma'lum yorliq" in matn(javob).lower()
    javob = mobil.topish(sorov(rf.get("/", {"q": nul, "bolim": xona.pk})), rv.pk)
    assert javob.status_code == 200
    data = {"bolim": xona.pk, "soni": "1", "usul": "qr", "qr_matn": f"DS|{nul}|X", "izoh": f"a{nul}b"}
    javob = mobil.saqla(sorov(rf.post("/", data)), rv.pk)
    assert javob.status_code == 200
    qayd = ReviziyaQayd.objects.get(reviziya=rv)
    assert (qayd.av, qayd.qr_matn, qayd.izoh) == (None, "DS||X", "ab")


def test_kartochka_standart_holati_boshqa_xonada(muhit, revizor, fa):
    from vositalar.models import Holat, Taqsimot

    rv, xona, stol, _ = muhit
    Taqsimot.objects.filter(av=stol).update(holat=Holat.NOSOZ)
    rv.kutilganlar.filter(av=stol).update(holat=Holat.NOSOZ)
    boshqa = Bolim.objects.create(filial=fa, nomi="Zal")
    c = kirgan(revizor)

    javob = c.get(url("mobil_topish", rv.pk, bolim=boshqa.pk, av=stol.pk))

    assert javob.status_code == 200
    t = matn(javob)
    assert f'<option value="{Holat.NOSOZ}" selected>' in t


def test_bir_bosishda_va_hammasi_joyida(muhit, revizor, foydalanuvchi, filial_yarat):
    rv, xona, stol, stul = muhit
    c = kirgan(revizor)
    html = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "Hammasi joyida" in html and "✓" in html and 'id="xona-chiziq"' in html

    # ✓ — qolgan soni bilan (stol: 2 dona) saqlaydi
    r = saqla(c, rv, xona, av=stol.pk, soni="2")
    assert r.status_code == 200 and ReviziyaQayd.objects.get(av=stol).soni == Decimal("2")
    assert 'id="xona-chiziq" aria-hidden="true" hx-swap-oob="true"' in r.content.decode()

    r = c.post(url("mobil_hammasi_bor", rv.pk), {"bolim": xona.pk})
    assert r.status_code == 200 and "1 ta AV belgilandi" in matn(r)
    assert ReviziyaQayd.objects.get(av=stul).soni == Decimal("1")
    assert ReviziyaQayd.objects.get(av=stol).soni == Decimal("2")  # allaqachon belgilangan — qo'shilmaydi
    assert "Bu xonada kutilgan hamma AV belgilangan" in matn(r)

    # boshqa filialdagi revizor — 404; GET — 405
    assert kirgan(foydalanuvchi("revizor", filiallar=[filial_yarat("99")])).post(url("mobil_hammasi_bor", rv.pk), {"bolim": xona.pk}).status_code == 404
    assert c.get(url("mobil_hammasi_bor", rv.pk)).status_code == 405


def test_usb_skaner_qr_matni_qidiruvda(muhit, revizor):
    rv, xona, stol, _ = muhit
    c = kirgan(revizor)
    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q=f"DS|{rv.filial.kod}|INV-1")))
    assert stol.nomi in html and 'name="av"' in html
    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="DS|99|INV-1")))
    assert "Noma'lum" in html or "noma'lum" in html


def test_revizor_ozi_reviziya_boshlaydi(fa, filial_yarat, revizor, foydalanuvchi):
    from reviziya.models import Reviziya

    revizor.first_name, revizor.last_name = "Ali", "Valiyev"
    revizor.save()
    kabinet = Bolim.objects.create(filial=fa, nomi="Kabinet")
    qator(av_yarat(fa, inv="INV-1"), fa, "1", bolim=kabinet)
    c = kirgan(revizor)

    html = matn(c.get(url("mobil_yangi")))
    assert f'value="f:{fa.pk}"' in html and f'value="b:{kabinet.pk}"' in html
    assert "Yangi reviziya boshlash" in matn(c.get(url("mobil")))

    r = c.post(url("mobil_yangi"), {"joy": f"b:{kabinet.pk}", "izoh": "Oylik"})
    rv = Reviziya.objects.get()
    assert r.status_code == 302 and r["Location"] == url("mobil_xonalar", rv.pk)
    assert (rv.filial, rv.bolim, rv.ochdi, rv.izoh) == (fa, kabinet, revizor, "Oylik")
    assert list(rv.revizorlar.all()) == [revizor]
    assert rv.komissiya == [{"xodim_id": None, "ism": "Ali Valiyev", "lavozim": "Revizor", "rol": "rais"}]
    assert rv.kutilganlar.count() == 1

    # qamrovi kesishgan ochiq reviziya — xato, yangi hujjat yo'q
    r = c.post(url("mobil_yangi"), {"joy": f"f:{fa.pk}"})
    assert r.status_code == 400 and "kesishgan" in matn(r) and Reviziya.objects.count() == 1
    # tanlanmagan / noto'g'ri qiymat
    assert c.post(url("mobil_yangi"), {"joy": "x:1"}).status_code == 400


def test_revizor_faqat_oz_filialida_boshlaydi(fa, filial_yarat, foydalanuvchi):
    from reviziya.models import Reviziya

    fb = filial_yarat("08")
    cheklangan = foydalanuvchi("revizor", [fa])
    c = kirgan(cheklangan)
    html = matn(c.get(url("mobil_yangi")))
    assert f'value="f:{fa.pk}"' in html and f'value="f:{fb.pk}"' not in html
    assert c.post(url("mobil_yangi"), {"joy": f"f:{fb.pk}"}).status_code == 400
    assert not Reviziya.objects.exists()
    # HR — reviziya o'tkazish huquqi yo'q
    assert kirgan(foydalanuvchi("hr")).get(url("mobil_yangi")).status_code == 403


def test_yangi_reviziya_ikki_qadamli_tanlov(fa, filial_yarat, revizor, hisobchi):
    fb = filial_yarat("08")
    bino = Bolim.objects.create(filial=fa, nomi="Bino")
    xona = Bolim.objects.create(filial=fa, ota=bino, nomi="Xona")
    ombor = Bolim.objects.create(filial=fa, nomi="Ombor")
    qator(av_yarat(fa, inv="INV-1", soni="3"), fa, "3", bolim=xona)
    c = kirgan(revizor)

    # 1-qadam: bir nechta filial — ro'yxat
    javob = c.get(url("mobil_yangi"))
    assert {v["f"] for v in javob.context["filiallar"]} == {fa, fb}
    assert "1-qadam" in matn(javob) and f'href="?filial={fa.pk}"' in matn(javob)

    # 2-qadam: tanlangan filial — butun filial + bo'limlar (AV soni ichki bo'limlari bilan)
    reviziya_och(fa, xona, [revizor], [], hisobchi)  # «Xona» band
    javob = c.get(url("mobil_yangi", filial=fa.pk))
    v = {x["nomi"]: x for x in javob.context["variantlar"]}
    assert (v["Bino"]["soni"], v["Xona"]["soni"], v["Ombor"]["soni"]) == (3, 3, 0)
    # ochiq reviziya bilan kesishadiganlar: butun filial, Bino (otasi), Xona; Ombor — bo'sh
    assert (v["Butun filial"]["band"], v["Bino"]["band"], v["Xona"]["band"], v["Ombor"]["band"]) == (True, True, True, False)
    html = matn(javob)
    assert f'value="b:{ombor.pk}" required' in html and f'value="b:{xona.pk}" disabled' in html
    assert "ochiq reviziya bor" in html

    r = c.post(url("mobil_yangi"), {"filial": fa.pk, "joy": f"b:{ombor.pk}"})
    assert r.status_code == 302


def test_yangi_reviziya_hammasi_band(fa, filial_yarat, revizor, hisobchi):
    fb = filial_yarat("08")
    reviziya_och(fb, None, [revizor], [], hisobchi)
    html = matn(kirgan(revizor).get(url("mobil_yangi", filial=fb.pk)))
    assert "hamma joyida ochiq reviziya bor" in html and "Reviziyani boshlash</button>" not in html


def test_mol_korinadi_va_mol_boyicha_qidiriladi(fa, revizor, hisobchi):
    import uuid

    from onec.models import Xodim

    xona = Bolim.objects.create(filial=fa, nomi="Kabinet")
    bobur = Xodim.objects.create(ref_1c=uuid.uuid4(), ism=" Bobur Aliyev", filial=fa)
    stol, stul = av_yarat(fa, inv="INV-1"), av_yarat(fa, inv="INV-2")
    qator(stol, fa, "1", bolim=xona, mol=bobur)
    qator(stul, fa, "1", bolim=xona)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    c = kirgan(revizor)

    html = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "МОЛ: Bobur Aliyev" in html and "МОЛ'siz" in html
    assert 'data-qolgan="' in html and "bobur aliyev" in html  # ro'yxat filtri МОЛ ismi bo'yicha ham

    # asosiy qidiruv: МОЛ ismi bo'yicha — yagona natija kartochkasi, unda МОЛ ko'rinadi
    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="bobur")))
    assert stol.nomi in html and "МОЛ: Bobur Aliyev" in html and "AV tarixi" in html


def test_av_tarixi_mobil(fa, revizor, hisobchi, foydalanuvchi, filial_yarat):
    xona = Bolim.objects.create(filial=fa, nomi="Kabinet")
    stol = av_yarat(fa, inv="INV-1")
    q = qator(stol, fa, "1")
    from vositalar import amallar

    amallar.kochir(q, "1", xona, hisobchi)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    c = kirgan(revizor)

    html = matn(c.get(url("mobil_tarix", rv.pk, av=stol.pk)))
    assert "Kabinet" in html and "m-tarix" in html
    assert c.get(url("mobil_tarix", rv.pk, av=999999)).status_code == 404
    assert kirgan(foydalanuvchi("revizor", filiallar=[filial_yarat("99")])).get(url("mobil_tarix", rv.pk, av=stol.pk)).status_code == 404


def test_reviziyadan_keyin_biriktirilgan_mol_korinadi(fa, revizor, hisobchi):
    """МОЛ reviziya suratidan emas, joriy taqsimotdan: reviziya ochilgach akt bilan biriktirilgan ham ko'rinadi."""
    import uuid

    from onec.models import Xodim

    xona = Bolim.objects.create(filial=fa, nomi="Prixod")
    pc = av_yarat(fa, inv="INV_100392")
    q = qator(pc, fa, "1", bolim=xona)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    q.mol = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Akbarov Burxonjon (kassir)", filial=fa)
    q.save()
    c = kirgan(revizor)

    assert "МОЛ: Akbarov Burxonjon (kassir)" in matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="akbarov")))
    assert pc.nomi in html and "МОЛ: Akbarov Burxonjon (kassir)" in html


def test_boshqaning_qaydi_revizor_ham_tuzatadi(muhit, revizor, hisobchi, foydalanuvchi):
    """Revizor reviziyani boshqaradi: boshqa foydalanuvchi qaydi ham qulfsiz, tuzatish maydoni bilan."""
    rv, xona, stol, _ = muhit
    ikkinchi = foydalanuvchi("revizor")
    rv.revizorlar.add(ikkinchi)
    qayd_qosh(rv, xona, hisobchi, av=stol, soni=Decimal("2"))  # boshqa foydalanuvchi qaydi

    html = matn(kirgan(ikkinchi).get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert "🔒" not in html and 'aria-label="Topilgan soni"' in html


def test_reviziyada_mol_biriktirish_qoralama_akt(fa, revizor, hisobchi, foydalanuvchi, filial_yarat):
    import uuid

    from mol.models import MolAkt
    from onec.models import Xodim

    xona = Bolim.objects.create(filial=fa, nomi="Prixod")
    pc, monitor = av_yarat(fa, inv="INV-PC"), av_yarat(fa, inv="INV-MON", soni="2")
    q1 = qator(pc, fa, "1", bolim=xona)
    qator(monitor, fa, "2", bolim=xona)
    kassir = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Akbarov Burxonjon (kassir)", filial=fa)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    c = kirgan(revizor)

    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, av=pc.pk)))
    assert "Javobgar shaxsni (МОЛ) biriktirish" in html and f'data-xodim="{kassir.pk}" data-xodim-nomi="Akbarov Burxonjon (kassir)"' in html

    r = c.post(url("mobil_mol", rv.pk), {"av": pc.pk, "xodim": kassir.pk})
    assert r.status_code == 200 and "qoralama aktga qo'shildi" in matn(r)
    c.post(url("mobil_mol", rv.pk), {"av": monitor.pk, "xodim": kassir.pk})
    akt = MolAkt.objects.get()  # ikkalasi bitta qoralama aktda
    assert (akt.holat, akt.topshiruvchi, akt.qabul_qiluvchi, akt.tuzdi) == ("qoralama", None, kassir, revizor)
    assert akt.izoh == f"{rv.nomi} reviziyasi bo'yicha"
    assert sorted((q.av_id, q.soni) for q in akt.qatorlar.all()) == sorted([(pc.pk, Decimal("1")), (monitor.pk, Decimal("2"))])
    q1.refresh_from_db()
    assert q1.mol is None  # tasdiqlanmaguncha taqsimot o'zgarmaydi

    # takror — qator ikki marta qo'shilmaydi
    r = c.post(url("mobil_mol", rv.pk), {"av": pc.pk, "xodim": kassir.pk})
    assert "allaqachon qoralama aktda" in matn(r) and akt.qatorlar.count() == 2
    # xodim tanlanmagan — 400; boshqa filialdagi revizor — 404
    assert c.post(url("mobil_mol", rv.pk), {"av": pc.pk}).status_code == 400
    assert kirgan(foydalanuvchi("revizor", filiallar=[filial_yarat("99")])).post(url("mobil_mol", rv.pk), {"av": pc.pk, "xodim": kassir.pk}).status_code == 404


def test_boshqa_filial_av_inv_raqam_bilan(muhit, revizor, filial_yarat):
    """Inv. raqam shu filialda topilmasa — boshqa filiallardan aniq moslik: kartochka qaysi filialniki ekanini
    aytadi va «ortiqcha (boshqa filial)» qilib saqlaydi (QR bilan skanerlagandek)."""
    from reviziya.solishtir import solishtir

    rv, xona, *_ = muhit
    fb = filial_yarat("02", "Showroom")
    begona = av_yarat(fb, inv="INV_100652")
    c = kirgan(revizor)

    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="INV_100652")))
    assert "Boshqa filial yorlig'i" in html and begona.nomi in html and "Showroom" in html
    assert 'name="qr_matn" value="DS|02|INV_100652"' in html

    assert saqla(c, rv, xona, qr_matn="DS|02|INV_100652", usul="qidiruv").status_code == 200
    [q] = [q for q in solishtir(rv) if q.guruh == "ortiqcha"]
    assert q.av_id is None and q.izoh == "boshqa filial" and q.qr_matn == "DS|02|INV_100652"
    # QR orqali ham AV nomi va filiali ko'rinadi; inv. raqam qismi (kamida 5 belgi) bilan ham topiladi
    assert "Showroom" in matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, qr="DS|02|INV_100652")))
    assert 'value="DS|02|INV_100652"' in matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="00652")))
    assert "Hech narsa topilmadi" in matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="0652")))


def test_boshqa_filialda_bir_nechta_moslik_royxat(muhit, revizor, filial_yarat):
    rv, xona, *_ = muhit
    av_yarat(filial_yarat("02", "Showroom"), inv="INV-9")
    av_yarat(filial_yarat("03", "Yaypan"), inv="INV-9")
    html = matn(kirgan(revizor).get(url("mobil_topish", rv.pk, bolim=xona.pk, q="INV-9")))
    assert "Boshqa filiallarda" in html and "Showroom" in html and "Yaypan" in html
    assert "qr=DS%7C02%7CINV-9" in html and "qr=DS%7C03%7CINV-9" in html


def test_boshqa_filial_qaydi_nomi_bilan_va_qisqa_sorov_izohi(muhit, revizor, filial_yarat):
    """Oxirgi belgilanganlarda boshqa filial qaydi «Noma'lum yorliq» emas — AV nomi va filiali; qisqa so'rovda
    boshqa filiallardan qidirish uchun kamida 5 belgi kerakligi aytiladi."""
    rv, xona, *_ = muhit
    begona = av_yarat(filial_yarat("02", "Showroom"), inv="INV_100569")
    c = kirgan(revizor)
    saqla(c, rv, xona, qr_matn="DS|02|INV_100569")
    html = matn(c.get(url("mobil_skan", rv.pk, bolim=xona.pk)))
    assert begona.nomi in html and "Showroom" in html and "Noma'lum yorliq" not in html

    html = matn(c.get(url("mobil_topish", rv.pk, bolim=xona.pk, q="787")))
    assert "Hech narsa topilmadi" in html and "kamida 5 belgi" in html
