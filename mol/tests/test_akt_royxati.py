"""МОЛ aktlari ro'yxati va qoralamani bekor qilish."""
import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from mol.models import MolAkt
from mol.servis import AktXato, akt_bekor_qil, akt_tasdiqla, akt_yarat
from onec.models import Xodim
from vositalar.models import Taqsimot
from vositalar.tarix import tarix

from .test_views import av_yarat, client_user, qator

SON = Decimal
ROYXAT = "mol:akt_royxat"


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def bobur(filial):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Bobur", filial=filial)


@pytest.fixture
def aziz(filial):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Aziz", filial=filial)


@pytest.fixture
def hr(foydalanuvchi):
    return foydalanuvchi("hr")


def _akt(filial, bobur, aziz, kim, kod="1"):
    av = av_yarat(filial, "6", "600", kod, f"Stol{kod}")
    return akt_yarat(bobur, aziz, [(qator(av, filial, "6", bobur), SON("2"))], kim=kim)


def test_royxat_hamma_holatlar(filial, bobur, aziz, hr):
    qoralama = _akt(filial, bobur, aziz, hr, "1")
    tasdiqlangan = _akt(filial, bobur, aziz, hr, "2")
    akt_tasdiqla(tasdiqlangan, hr)
    bekor = _akt(filial, bobur, aziz, hr, "3")
    akt_bekor_qil(bekor, hr)
    javob = client_user(hr).get(reverse(ROYXAT))
    assert javob.status_code == 200
    assert [a.pk for a in javob.context["sahifa"]] == [bekor.pk, tasdiqlangan.pk, qoralama.pk]  # yangisi tepada
    html = javob.content.decode()
    for a in (qoralama, tasdiqlangan, bekor):
        assert reverse("mol:akt", args=[a.pk]) in html


@pytest.mark.parametrize("holat", ["qoralama", "tasdiqlangan", "bekor"])
def test_royxat_holat_filtri(filial, bobur, aziz, hr, holat):
    aktlar = {"qoralama": _akt(filial, bobur, aziz, hr, "1"), "tasdiqlangan": _akt(filial, bobur, aziz, hr, "2"),
              "bekor": _akt(filial, bobur, aziz, hr, "3")}
    akt_tasdiqla(aktlar["tasdiqlangan"], hr)
    akt_bekor_qil(aktlar["bekor"], hr)
    javob = client_user(hr).get(reverse(ROYXAT), {"holat": holat})
    assert [a.pk for a in javob.context["sahifa"]] == [aktlar[holat].pk]


def test_royxat_qidiruv_raqam_va_xodim(filial, bobur, aziz, hr):
    birinchi = _akt(filial, bobur, aziz, hr, "1")
    ikkinchi = _akt(filial, bobur, aziz, hr, "2")
    c = client_user(hr)
    assert [a.pk for a in c.get(reverse(ROYXAT), {"q": ikkinchi.nomi}).context["sahifa"]] == [ikkinchi.pk]
    assert {a.pk for a in c.get(reverse(ROYXAT), {"q": "aziz"}).context["sahifa"]} == {birinchi.pk, ikkinchi.pk}
    assert list(c.get(reverse(ROYXAT), {"q": "yo'q-odam"}).context["sahifa"]) == []


def test_royxat_filial_cheklovi(foydalanuvchi, filial, filial_yarat, bobur, aziz, hr):
    meniki = _akt(filial, bobur, aziz, hr)
    boshqa = filial_yarat("B")
    begona = akt_yarat(None, aziz, [(qator(av_yarat(boshqa, kod="9"), boshqa, "1"), SON("1"))], kim=hr)
    javob = client_user(foydalanuvchi("hisobchi", [filial])).get(reverse(ROYXAT))
    assert [a.pk for a in javob.context["sahifa"]] == [meniki.pk]
    assert begona.pk not in [a.pk for a in javob.context["sahifa"]]


def test_royxat_notogri_parametrlar(filial, bobur, aziz, hr):
    _akt(filial, bobur, aziz, hr)
    javob = client_user(hr).get(reverse(ROYXAT), {"holat": "boshqa", "page": "x", "dan": "abc"})
    assert javob.status_code == 200


def test_bekor_qilish_servisi(filial, bobur, aziz, hr):
    akt = _akt(filial, bobur, aziz, hr)
    akt_bekor_qil(akt, hr)
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.BEKOR
    assert akt.bekor_qildi == hr and akt.bekor_vaqti is not None
    assert Taqsimot.objects.get(mol=bobur).soni == SON("6")  # taqsimot o'zgarmaydi
    with pytest.raises(AktXato):
        akt_tasdiqla(akt, hr)  # bekor qilingan akt tasdiqlanmaydi
    with pytest.raises(AktXato):
        akt_bekor_qil(akt, hr)


def test_tasdiqlangan_akt_bekor_qilinmaydi(filial, bobur, aziz, hr):
    akt = _akt(filial, bobur, aziz, hr)
    akt_tasdiqla(akt, hr)
    with pytest.raises(AktXato):
        akt_bekor_qil(akt, hr)
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.TASDIQLANGAN


def test_bekor_qilish_sahifadan(filial, bobur, aziz, hr):
    akt = _akt(filial, bobur, aziz, hr)
    c = client_user(hr)
    sahifa = c.get(reverse("mol:akt", args=[akt.pk])).content.decode()
    assert reverse("mol:akt_bekor", args=[akt.pk]) in sahifa
    javob = c.post(reverse("mol:akt_bekor", args=[akt.pk]), follow=True)
    assert javob.status_code == 200
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.BEKOR
    sahifa = javob.content.decode()
    assert reverse("mol:akt_bekor", args=[akt.pk]) not in sahifa
    assert reverse("mol:akt_tasdiqla", args=[akt.pk]) not in sahifa
    assert "Bekor qilingan" in sahifa


def test_bekor_qilish_huquqi_va_get(client_rol, filial, bobur, aziz, hr):
    akt = _akt(filial, bobur, aziz, hr)
    assert client_rol("rahbar").post(reverse("mol:akt_bekor", args=[akt.pk])).status_code == 403
    assert client_user(hr).get(reverse("mol:akt_bekor", args=[akt.pk])).status_code == 405
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.QORALAMA


def test_bekor_qilish_begona_filial_404(foydalanuvchi, filial, filial_yarat, aziz, hr):
    boshqa = filial_yarat("B")
    akt = akt_yarat(None, aziz, [(qator(av_yarat(boshqa, kod="9"), boshqa, "1"), SON("1"))], kim=hr)
    javob = client_user(foydalanuvchi("hisobchi", [filial])).post(reverse("mol:akt_bekor", args=[akt.pk]))
    assert javob.status_code == 404
    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.QORALAMA


def test_bekor_qilingan_akt_tarixda(filial, bobur, aziz, hr):
    akt = _akt(filial, bobur, aziz, hr)
    akt_bekor_qil(akt, hr)
    matnlar = [q.matn for q in tarix(akt.qatorlar.get().av, hr)]
    assert any(akt.nomi in m and "bekor qilingan" in m for m in matnlar)


def test_menyu_va_xodimlar_sahifasida_havola(client_rol):
    html = client_rol("hr").get(reverse("mol:xodimlar")).content.decode()
    assert f'href="{reverse(ROYXAT)}"' in html
