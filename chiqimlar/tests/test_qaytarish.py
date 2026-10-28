"""1C'da bekor qilingan tasdiqlangan chiqim: aniqlash, xabar, «Tasdiqni qaytarish»; tasdiqni qo'lda bekor qilish;
chiqim tarixi."""
import uuid
from datetime import datetime, timedelta, timezone as dt_tz
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from chiqimlar.models import ChiqimHujjat
from chiqimlar.servis import ChiqimXato, chiqim_tarixi, chiqimlarni_yangila, tasdiqla, tasdiqni_qaytar
from onec.models import AV, AVQoldiq, Harakat1C, Xodim
from vositalar.models import Bolim, Holat, Sozlama, Taqsimot, TaqsimotHarakat
from vositalar.moslash import farq, moslashtir

pytestmark = pytest.mark.django_db

SON = Decimal
BOSH = datetime(2026, 9, 1, tzinfo=dt_tz.utc)
DAN = datetime(2026, 8, 1, tzinfo=dt_tz.utc)
GACHA = datetime(2026, 12, 31, tzinfo=dt_tz.utc)
SANA = datetime(2026, 9, 10, 12, 0, tzinfo=dt_tz.utc)


@pytest.fixture(autouse=True)
def boshlanish():
    Sozlama.objects.update_or_create(pk=1, defaults={"chiqim_boshlanishi": BOSH})


@pytest.fixture
def muhit(filial_yarat, foydalanuvchi):
    """A filial: AV 3 dona (Ofis — 2, Ali; Ombor — 1); 1C'da 1 dona sotilgan (qoldiq 2), chiqim kutilmoqda."""
    fa = filial_yarat("A")
    av = AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")
    ofis = Bolim.objects.create(filial=fa, nomi="Ofis")
    ombor = Bolim.objects.create(filial=fa, nomi="Ombor")
    ali = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Ali")
    Taqsimot.objects.create(av=av, filial=fa, bolim=ofis, mol=ali, holat=Holat.ISHLATILMOQDA, soni=SON("2"))
    Taqsimot.objects.create(av=av, filial=fa, bolim=ombor, holat=Holat.ZAXIRADA, soni=SON("1"))
    AVQoldiq.objects.create(av=av, filial=fa, soni=SON("2"), summa=SON("200"))
    ref = uuid.uuid4()
    harakat = Harakat1C.objects.create(
        sana=SANA, hujjat_turi="Реализация", hujjat_raqami="17", hujjat_ref=ref,
        av=av, filial=fa, vid="chiqim", soni=SON("1"), summa=SON("100"),
    )
    chiqimlarni_yangila(DAN, GACHA)
    c = ChiqimHujjat.objects.get()
    return {"fa": fa, "av": av, "ofis": ofis, "ombor": ombor, "ali": ali, "c": c, "harakat": harakat,
            "hisobchi": foydalanuvchi("hisobchi")}


def taqsimot(av):
    return sorted(
        ((t.bolim_id, t.mol_id, t.holat, t.soni) for t in Taqsimot.objects.filter(av=av)),
        key=lambda x: (x[0] or 0, x[1] or 0, x[2], x[3]),
    )


def ofisdan_tasdiqla(m):
    qator = Taqsimot.objects.get(av=m["av"], bolim=m["ofis"])
    tasdiqla(m["c"], "sotildi", {qator.pk: SON("1")}, m["hisobchi"], kutilgan_soni=SON("1"))
    m["c"].refresh_from_db()


def test_tasdiqlashda_ayirilgan_qatorlar_saqlanadi(muhit):
    m = muhit
    ofisdan_tasdiqla(m)
    assert m["c"].ayirilganlar == [
        {"bolim": m["ofis"].pk, "mol": m["ali"].pk, "holat": "ishlatilmoqda", "soni": "1.000"}
    ]


def test_1c_da_bekor_qilingan_tasdiqlangan_aniqlanadi_va_qaytariladi(muhit):
    m = muhit
    oldin_tasdiq = taqsimot(m["av"])
    ofisdan_tasdiqla(m)
    # 1C'da hujjat bekor qilindi: harakat yo'qoladi, qoldiq qaytadi; sinxron tartibi — chiqimlar, keyin moslash
    m["harakat"].delete()
    AVQoldiq.objects.filter(av=m["av"]).update(soni=SON("3"))
    stat = chiqimlarni_yangila(DAN, GACHA)
    moslashtir()

    m["c"].refresh_from_db()
    assert m["c"].holat == ChiqimHujjat.Holat.BEKOR_1C and stat["bekor_1c"] == 1
    # moslash qaytgan donani «taqsimlanmagan» ga qo'ydi — AV o'z joyini yo'qotgan
    assert (None, None, "ishlatilmoqda", SON("1")) in taqsimot(m["av"])

    tasdiqni_qaytar(m["c"], m["hisobchi"])

    m["c"].refresh_from_db()
    assert m["c"].holat == ChiqimHujjat.Holat.BEKOR
    # Ali'dagi ofis qatori tiklandi, «taqsimlanmagan» bo'shadi — sotilishdan oldingi holat
    assert taqsimot(m["av"]) == sorted(oldin_tasdiq)
    assert farq(m["av"], m["fa"]) == 0
    h = TaqsimotHarakat.objects.filter(sabab=TaqsimotHarakat.Sabab.CHIQIM_QAYTARILDI).get()
    assert (h.yangi_bolim, h.yangi_mol, h.soni) == (m["ofis"], m["ali"], SON("1"))


def test_bekor_1c_qayta_otkazilsa_tasdiqlanganga_qaytadi(muhit):
    m = muhit
    ofisdan_tasdiqla(m)
    harakat = m["harakat"]
    malumot = {f: getattr(harakat, f) for f in ("sana", "hujjat_turi", "hujjat_raqami", "hujjat_ref", "av", "filial",
                                                 "vid", "soni", "summa")}
    harakat.delete()
    chiqimlarni_yangila(DAN, GACHA)
    m["c"].refresh_from_db()
    assert m["c"].holat == ChiqimHujjat.Holat.BEKOR_1C
    Harakat1C.objects.create(**malumot)  # 1C'da qayta o'tkazildi
    chiqimlarni_yangila(DAN, GACHA)
    m["c"].refresh_from_db()
    assert m["c"].holat == ChiqimHujjat.Holat.TASDIQLANGAN


def test_tasdiqni_qolda_bekor_qilish_kutilmoqdaga_qaytaradi(muhit):
    m = muhit
    oldin = taqsimot(m["av"])
    ofisdan_tasdiqla(m)

    tasdiqni_qaytar(m["c"], m["hisobchi"])

    m["c"].refresh_from_db()
    assert (m["c"].holat, m["c"].tur, m["c"].kim, m["c"].ayirilganlar) == (ChiqimHujjat.Holat.KUTILMOQDA, "", None, [])
    assert taqsimot(m["av"]) == oldin
    assert farq(m["av"], m["fa"]) == 0
    # yana tasdiqlash mumkin
    ofisdan_tasdiqla(m)
    assert m["c"].holat == ChiqimHujjat.Holat.TASDIQLANGAN


def test_qaytarish_faqat_tasdiqlangan_yoki_bekor_1c(muhit):
    with pytest.raises(ChiqimXato):
        tasdiqni_qaytar(muhit["c"], muhit["hisobchi"])  # kutilmoqda


def test_chiqim_tarixi_va_sahifa(muhit):
    m = muhit
    ofisdan_tasdiqla(m)
    tasdiqni_qaytar(m["c"], m["hisobchi"])
    ofisdan_tasdiqla(m)

    tarix = chiqim_tarixi(m["c"])
    matnlar = [t["matn"] for t in tarix]
    assert matnlar[0].startswith("1C'dan keldi")
    assert sum("Tasdiqlandi" in t for t in matnlar) == 2 and any("Tasdiq bekor qilindi" in t for t in matnlar)
    assert any("Ofis" in t and "Ali" in t for t in matnlar)  # qaysi qatordan ayirilgani
    assert [t["vaqt"] for t in tarix] == sorted(t["vaqt"] for t in tarix)

    c = Client()
    c.force_login(m["hisobchi"])
    url = reverse("chiqimlar:tasdiqlash", args=[m["c"].pk])
    html = c.get(url).content.decode()
    assert "Tarix" in html and "Tasdiqni bekor qilish" in html
    assert c.post(reverse("chiqimlar:qaytar", args=[m["c"].pk])).status_code == 302
    m["c"].refresh_from_db()
    assert m["c"].holat == ChiqimHujjat.Holat.KUTILMOQDA
    assert Client().post(reverse("chiqimlar:qaytar", args=[m["c"].pk])).status_code == 302  # kirmagan — login'ga


def test_bekor_1c_menyu_belgisida_va_royxatda(muhit):
    m = muhit
    ofisdan_tasdiqla(m)
    m["harakat"].delete()
    chiqimlarni_yangila(DAN, GACHA)
    c = Client()
    c.force_login(m["hisobchi"])
    javob = c.get(reverse("panel:bosh"), follow=True)
    assert javob.context["chiqim_kutilmoqda_soni"] == 1  # kutilmoqda 0 + 1C'da bekor 1
    html = c.get(reverse("chiqimlar:royxat"), {"holat": "bekor_1c"}).content.decode()
    assert "Реализация 17" in html or "17" in html
    html = c.get(reverse("chiqimlar:tasdiqlash", args=[m["c"].pk])).content.decode()
    assert "1C&#x27;da bekor qilindi" in html or "1C'da bekor qilindi" in html
    assert "Tasdiqni qaytarish" in html


def test_umumiy_amallar_tarixi(muhit, filial_yarat, foydalanuvchi):
    """Barcha chiqimlar tarixi: tasdiq, 1C bekori va qaytarish (kim, amal), filtr; boshqa filial chiqimi ko'rinmaydi."""
    m = muhit
    ofisdan_tasdiqla(m)
    m["harakat"].delete()
    AVQoldiq.objects.filter(av=m["av"]).update(soni=SON("3"))
    chiqimlarni_yangila(DAN, GACHA)
    moslashtir()
    m["c"].refresh_from_db()
    tasdiqni_qaytar(m["c"], m["hisobchi"])

    c = Client()
    c.force_login(m["hisobchi"])
    url = reverse("chiqimlar:tarix")
    assert f'href="{url}"' in c.get(reverse("chiqimlar:royxat")).content.decode()
    javob = c.get(url)
    matnlar = [q["matn"] for q in javob.context["qatorlar"]]
    assert matnlar == [
        "Tasdiq qaytarildi — donalar asl joyiga qo'yildi",
        "1C'da hujjat bekor qilindi — tasdiqni qaytarish kerak",
        "Tasdiqlandi",
    ]
    assert all(q["c"].pk == m["c"].pk for q in javob.context["qatorlar"])
    assert [q["matn"] for q in c.get(url, {"amal": "tasdiq"}).context["qatorlar"]] == ["Tasdiqlandi"]
    assert [q["j"].kim_nomi for q in c.get(url, {"kim": "1C"}).context["qatorlar"]] == ["1C sinxron"]

    # Boshqa filialda cheklangan foydalanuvchi bu chiqimlar tarixini ko'rmaydi
    boshqa = Client()
    boshqa.force_login(foydalanuvchi("hisobchi", filiallar=[filial_yarat("B")]))
    assert boshqa.get(url).context["qatorlar"] == []
