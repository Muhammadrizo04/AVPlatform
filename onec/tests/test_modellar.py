import uuid
from decimal import Decimal

import pytest
from django.db.models import ProtectedError

from onec.models import AV, AVQoldiq, Harakat1C, Xodim


@pytest.fixture
def av_yarat(db):
    def yarat():
        return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")

    return yarat


def test_filialni_ochirib_bolmaydi(av_yarat, filial_yarat):
    filial = filial_yarat("001")
    AVQoldiq.objects.create(av=av_yarat(), filial=filial, soni=Decimal("1"), summa=Decimal("10"))

    with pytest.raises(ProtectedError):
        filial.delete()


def test_avni_ochirib_bolmaydi(av_yarat, filial_yarat):
    av = av_yarat()
    Harakat1C.objects.create(
        sana="2026-09-01T10:00:00Z", hujjat_turi="X", hujjat_raqami="1",
        hujjat_ref=uuid.uuid4(), av=av, vid="kirim", soni=Decimal("1"), summa=Decimal("0"),
    )

    with pytest.raises(ProtectedError):
        av.delete()


def test_xodim_filialsiz_bolishi_mumkin(db):
    xodim = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Vali")

    assert xodim.filial is None
