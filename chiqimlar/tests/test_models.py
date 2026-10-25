import uuid

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from chiqimlar.models import ChiqimHujjat
from onec.models import AV
from vositalar.models import Sozlama, TaqsimotHarakat


def _chiqim(av, filial, ref, **kw):
    return ChiqimHujjat.objects.create(
        hujjat_turi="Реализация",
        hujjat_raqami="1",
        hujjat_ref=ref,
        sana=timezone.now(),
        av=av,
        filial=filial,
        soni=1,
        summa=100,
        taxmin_tur=ChiqimHujjat.Tur.SOTILDI,
        **kw,
    )


@pytest.fixture
def av(db):
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


@pytest.mark.django_db
def test_unikal_hujjat_av_filial(av, filial_yarat):
    filial = filial_yarat("F1")
    ref = uuid.uuid4()
    _chiqim(av, filial, ref)
    with pytest.raises(IntegrityError), transaction.atomic():
        _chiqim(av, filial, ref)


@pytest.mark.django_db
def test_standart_holat_kutilmoqda(av, filial_yarat):
    chiqim = _chiqim(av, filial_yarat("F1"), uuid.uuid4())
    assert chiqim.holat == ChiqimHujjat.Holat.KUTILMOQDA


@pytest.mark.django_db
def test_chiqim_boshlanishi_migratsiyada_toldirilgan():
    assert Sozlama.ol().chiqim_boshlanishi is not None


def test_sabab_qiymatlari():
    assert TaqsimotHarakat.Sabab.SOTILDI == "sotildi"
    assert TaqsimotHarakat.Sabab.OTKAZILDI == "otkazildi"
    assert TaqsimotHarakat.Sabab.HISOBDAN_CHIQARILDI == "hisobdan_chiqarildi"
