"""Javobgar shaxslar: 1C'da o'chirilgan xodim ketgan hisoblanadi, filial filtri."""
from datetime import date
from decimal import Decimal as D

import pytest
from django.test import Client
from django.urls import reverse

from mol.servis import AktXato, akt_tasdiqla, akt_yarat
from mol.sorovlar import faol_xodimlar
from vositalar.bayroqlar import BAYROQLAR
from vositalar.tests.test_bayroqlar import av_yarat, qator, xodim

pytestmark = pytest.mark.django_db


@pytest.fixture
def x(filial_yarat):
    return filial_yarat("01")


@pytest.fixture
def y(filial_yarat):
    return filial_yarat("02")


def kirgan(u):
    c = Client()
    c.force_login(u)
    return c


def sahifa(u, **params):
    return kirgan(u).get(reverse("mol:xodimlar"), params)


def test_ochirilgan_xodim_qabul_qila_olmaydi(x, foydalanuvchi):
    assert not faol_xodimlar(foydalanuvchi("admin")).filter(pk=xodim(filial=x, ochirilgan=True).pk).exists()


def test_ochirilgan_xodimdagi_av_ketgan_royxatida(x, foydalanuvchi):
    t = qator(av_yarat(x), x, "1", mol=xodim(filial=x, ochirilgan=True))

    assert list(BAYROQLAR["ketgan_xodimda"].so_rov(foydalanuvchi("admin"), date.today())) == [t]


def test_ochirilgan_xodimga_akt_tasdiqlanmaydi(x, foydalanuvchi):
    u = foydalanuvchi("hisobchi")
    qabul, top = xodim(filial=x), xodim(filial=x)
    t = qator(av_yarat(x), x, "1", mol=top)
    akt = akt_yarat(top, qabul, [(t, t.soni)], u)
    type(qabul).objects.filter(pk=qabul.pk).update(ochirilgan=True)

    with pytest.raises(AktXato, match="faol xodim emas"):
        akt_tasdiqla(akt, u)


def test_sahifada_ochirilgan_xodim_ketgan(x, foydalanuvchi):
    o = xodim(filial=x, ochirilgan=True)
    u = foydalanuvchi("admin")

    assert o in list(sahifa(u, holat="ketgan").context["xodimlar"])
    assert o not in list(sahifa(u, holat="faol").context["xodimlar"])


def test_filial_filtri_xodimlari(x, y, foydalanuvchi):
    shu, boshqa, kelgan = xodim(filial=x), xodim(filial=y), xodim(filial=y)
    qator(av_yarat(x), x, "1", mol=kelgan)  # Y xodimi, lekin X filialidagi AV unda

    r = sahifa(foydalanuvchi("admin"), filial=x.pk)

    assert set(r.context["xodimlar"]) == {shu, kelgan} and boshqa not in r.context["xodimlar"]


def test_filial_filtrida_av_soni_faqat_shu_filial(x, y, foydalanuvchi):
    k = xodim(filial=x)
    qator(av_yarat(x, inv="A", soni="2"), x, "2", mol=k)
    qator(av_yarat(y, inv="B", soni="3"), y, "3", mol=k)
    u = foydalanuvchi("admin")

    assert next(i for i in sahifa(u).context["xodimlar"] if i == k).av_soni == D("5")
    assert next(i for i in sahifa(u, filial=x.pk).context["xodimlar"] if i == k).av_soni == D("2")


def test_filial_filtrida_korsatkichlar_shu_filial(x, y, foydalanuvchi):
    xodim(filial=x)
    xodim(filial=y)

    assert sahifa(foydalanuvchi("admin"), filial=x.pk).context["korsatkichlar"]["faol"] == 1


def test_ruxsatsiz_filial_filtrda_ishlamaydi(x, y, foydalanuvchi):
    shu, boshqa = xodim(filial=x), xodim(filial=y)
    r = sahifa(foydalanuvchi("hisobchi", filiallar=[x]), filial=y.pk)

    assert list(r.context["xodimlar"]) == [shu] and boshqa not in r.context["xodimlar"]
    assert list(r.context["filiallar"]) == [x]


def test_filtr_tanlovi_bir_necha_filialda_chiqadi(x, y, foydalanuvchi):
    assert 'name="filial"' in sahifa(foydalanuvchi("admin")).content.decode()
    assert 'name="filial"' not in sahifa(foydalanuvchi("hisobchi", filiallar=[x])).content.decode()
