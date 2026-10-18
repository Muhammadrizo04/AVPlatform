import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from onec.models import AV
from vositalar.models import Bolim, Holat, Sozlama, Taqsimot, YorliqOlchami


@pytest.fixture
def av(db):
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


def test_taqsimot_nulls_unikal(av, filial_yarat):
    filial = filial_yarat("001")
    Taqsimot.objects.create(av=av, filial=filial, holat=Holat.ISHLATILMOQDA, soni=Decimal("2"))

    with pytest.raises(IntegrityError), transaction.atomic():
        Taqsimot.objects.create(av=av, filial=filial, holat=Holat.ISHLATILMOQDA, soni=Decimal("1"))


def test_taqsimot_holat_farqi_unikallikni_buzmaydi(av, filial_yarat):
    filial = filial_yarat("001")
    Taqsimot.objects.create(av=av, filial=filial, holat=Holat.ISHLATILMOQDA, soni=Decimal("2"))

    Taqsimot.objects.create(av=av, filial=filial, holat=Holat.NOSOZ, soni=Decimal("1"))

    assert Taqsimot.objects.count() == 2


@pytest.mark.parametrize("soni", [Decimal("0"), Decimal("-1")])
def test_taqsimot_soni_musbat(av, filial_yarat, soni):
    with pytest.raises(IntegrityError), transaction.atomic():
        Taqsimot.objects.create(av=av, filial=filial_yarat("001"), holat=Holat.ZAXIRADA, soni=soni)


def test_holat_6_qiymat():
    assert [h.value for h in Holat] == [
        "ishlatilmoqda", "zaxirada", "tamirda", "nosoz", "hisobdan_chiqarishga", "topilmadi",
    ]


def test_bolim_toliq_nomi(filial_yarat):
    filial = filial_yarat("001")
    zal = Bolim.objects.create(filial=filial, nomi="Savdo zali")
    kassa = Bolim.objects.create(filial=filial, ota=zal, nomi="Kassa 2")

    assert zal.toliq_nomi == "Savdo zali"
    assert kassa.toliq_nomi == "Savdo zali / Kassa 2"


def test_sozlama_yagona(db):
    birinchi = Sozlama.ol()
    ikkinchi = Sozlama.ol()

    assert birinchi.pk == ikkinchi.pk
    assert Sozlama.objects.count() == 1


def test_yorliq_olchamlari_boshlangich(db):
    olchamlar = {o.nomi: o for o in YorliqOlchami.objects.all()}

    assert set(olchamlar) == {"40×30", "58×40"}
    assert olchamlar["58×40"].eni_mm == Decimal("58") and olchamlar["58×40"].boyi_mm == Decimal("40")
    assert YorliqOlchami.standarti().nomi == "40×30"


def test_yorliq_olchami_faqat_bitta_standart(db):
    with pytest.raises(IntegrityError), transaction.atomic():
        YorliqOlchami.objects.create(nomi="50×30", eni_mm=Decimal("50"), boyi_mm=Decimal("30"), standart=True)


@pytest.mark.parametrize("eni, boyi", [(19, 30), (121, 30), (40, 14), (40, 121)])
def test_yorliq_olchami_chegarasi(db, eni, boyi):
    with pytest.raises(IntegrityError), transaction.atomic():
        YorliqOlchami.objects.create(nomi="X", eni_mm=Decimal(eni), boyi_mm=Decimal(boyi))
