"""Dona narxi filial bo'yicha: filial va bo'lim hisobotlari, qaydnoma, akt va AV ro'yxati filtri bir xil raqam beradi."""
import uuid
from decimal import Decimal as D

import pytest
from django.urls import reverse
from django.utils import timezone

from chiqimlar.models import ChiqimHujjat
from hisobotlar import servis
from mol.servis import akt_tasdiqla, akt_yarat
from mol.sorovlar import xodim_yigindilari
from onec.models import AV, AVQoldiq
from vositalar.filtrlar import av_filtrla
from vositalar.models import Bolim, Taqsimot
from vositalar.narx import filial_narxlari
from vositalar.tests.test_bayroqlar import av_yarat, qator, qoldiq, xodim

pytestmark = pytest.mark.django_db


@pytest.fixture
def x(filial_yarat):
    return filial_yarat("01", "X")


@pytest.fixture
def y(filial_yarat):
    return filial_yarat("02", "Y")


@pytest.fixture
def admin(foydalanuvchi):
    return foydalanuvchi("admin")


@pytest.fixture
def ikki_filial(x, y):
    """Bir AV: X da 1 dona 100, Y da 1 dona 300."""
    av = av_yarat(x, soni="1")
    AVQoldiq.objects.create(av=av, filial=y, soni=D("1"), summa=D("300"))
    return av


def test_narx_filialdan_olinadi(x, y, ikki_filial):
    narx = filial_narxlari({ikki_filial.pk})

    assert (narx(ikki_filial.pk, x.pk), narx(ikki_filial.pk, y.pk)) == (D("100"), D("300"))


def test_filialda_qoldiq_yoq_bolsa_umumiy_ortacha(x, y, filial_yarat, ikki_filial):
    assert filial_narxlari({ikki_filial.pk})(ikki_filial.pk, filial_yarat("03").pk) == D("200")


def test_nol_donali_qator_narxga_kirmaydi(x, y):
    av = av_yarat(x, soni="1")
    AVQoldiq.objects.create(av=av, filial=y, soni=D("0"), summa=D("50"))

    assert filial_narxlari({av.pk})(av.pk, x.pk) == D("100")


def test_bolim_kesimi_filial_kesimiga_teng(x, y, admin, ikki_filial):
    qator(ikki_filial, x, "1", bolim=Bolim.objects.create(filial=x, nomi="A"))
    qator(ikki_filial, y, "1", bolim=Bolim.objects.create(filial=y, nomi="B"))
    bugun = timezone.localdate()

    bolim = {q["nomi"]: q["boshlangich"] for q in servis.kesim(admin, "bolim", bugun)}
    filial = {q["nomi"]: q["boshlangich"] for q in servis.kesim(admin, "filial", bugun)}

    assert bolim == {"X / A": D("100.00"), "Y / B": D("300.00")} and filial == {"X": D("100"), "Y": D("300")}


def test_qaydnomalar_filial_narxida(x, y, admin, ikki_filial):
    a = Bolim.objects.create(filial=y, nomi="B")
    m = xodim(filial=y)
    qator(ikki_filial, y, "1", bolim=a, mol=m)

    assert [q["qiymat"] for q in servis.mol_qaydnoma(admin)] == [D("300.00")]
    assert [q["qiymat"] for q in servis.bolim_qaydnoma(admin, y.pk)] == [D("300.00")]
    assert xodim_yigindilari(admin)[m.pk] == (D("1"), D("300"))


def test_akt_filial_narxida_saqlanadi(x, y, foydalanuvchi, ikki_filial):
    u = foydalanuvchi("hisobchi")
    top = xodim(filial=y)
    t = qator(ikki_filial, y, "1", mol=top)
    akt = akt_yarat(top, xodim(filial=y), [(t, t.soni)], u)

    akt_tasdiqla(akt, u)

    assert akt.qatorlar.get().dona_narxi == D("300.00")


def test_kutilayotgan_chiqimdagi_ortiqcha_dona_qiymatni_buzmaydi(x, admin):
    """1C: 3 dona (300), taqsimotda 5 (2 tasi chiqim tasdig'ini kutmoqda): dona narxi 100 — o'zgarmaydi."""
    av = av_yarat(x, soni="3")
    AVQoldiq.objects.filter(av=av).update(summa=D("300"))
    qator(av, x, "5", bolim=Bolim.objects.create(filial=x, nomi="A"))
    ChiqimHujjat.objects.create(
        hujjat_turi="РеализацияОС", hujjat_raqami="1", hujjat_ref=uuid.uuid4(), sana=timezone.now(), av=av, filial=x,
        soni=D("2"), summa=D("200"), taxmin_tur="sotildi",
    )

    assert [q["qiymat"] for q in servis.bolim_qaydnoma(admin, x.pk)] == [D("500.00")]


def test_filial_filtrida_soni_va_summasi_shu_filial(x, y, admin):
    av = av_yarat(x, soni="2")
    qoldiq(av, y, "3")

    hammasi = av_filtrla(AV.objects.all(), {}, admin).get(pk=av.pk)
    shu = av_filtrla(AV.objects.all(), {"filial": str(x.pk)}, admin).get(pk=av.pk)

    assert (hammasi.jami_soni, hammasi.jami_summa) == (D("5"), D("200"))
    assert (shu.jami_soni, shu.jami_summa) == (D("2"), D("100"))


def test_ruxsatsiz_filial_filtri_natija_bermaydi(x, y, foydalanuvchi):
    av = av_yarat(x, soni="2")
    qoldiq(av, y, "3")
    u = foydalanuvchi("hisobchi", filiallar=[x])

    assert not av_filtrla(AV.objects.all(), {"filial": str(y.pk)}, u).exists()


def test_royxatda_filial_ustuni_filtrdagi_filial(client_rol, x, y):
    av = av_yarat(y, soni="2")  # nomi bo'yicha X birinchi, filtr — Y
    qoldiq(av, x, "1")
    javob = client_rol("admin").get(reverse("vositalar:royxat"), {"filial": y.pk})

    assert next(a for a in javob.context["sahifa"] if a.pk == av.pk).joy_filial == "Y"
    assert Taqsimot.objects.count() == 0
