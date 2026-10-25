import uuid

import pytest

from jurnal.models import Jurnal
from jurnal.yoz import yoz
from onec.models import AV


@pytest.fixture
def av(db):
    return AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")


def test_jurnal_sinxron_nomi(av):
    yozuv = yoz(None, av, "nomi", "Eski", "Yangi")

    assert yozuv.kim is None
    assert yozuv.kim_nomi == "1C sinxron"


def test_jurnal_foydalanuvchi_va_obyekt(av, foydalanuvchi):
    user = foydalanuvchi("hisobchi")

    yozuv = yoz(user, av, "inv_raqam", "A1", None)

    yozuv.refresh_from_db()
    assert yozuv.kim == user
    assert yozuv.kim_nomi == user.username
    assert yozuv.obyekt_turi == "onec.av"
    assert yozuv.obyekt_id == str(av.pk)
    assert (yozuv.maydon, yozuv.eski, yozuv.yangi) == ("inv_raqam", "A1", "")
    assert Jurnal.objects.count() == 1


def test_jurnal_foydalanuvchi_ochirilsa_nom_qoladi(av, foydalanuvchi):
    user = foydalanuvchi("hisobchi")
    nomi = user.username
    yozuv = yoz(user, av, "izoh", 1, 2)

    user.delete()

    yozuv.refresh_from_db()
    assert yozuv.kim is None
    assert yozuv.kim_nomi == nomi
    assert (yozuv.eski, yozuv.yangi) == ("1", "2")
