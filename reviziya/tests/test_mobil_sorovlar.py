"""`/reviziya/m/` — ochiq reviziyalar soni oshganda so'rovlar soni oshmasligi kerak (oldin har reviziyaga 2 ta)."""
import uuid
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from onec.models import AV, AVQoldiq
from reviziya.servis import qayd_qosh, reviziya_och
from vositalar.models import Holat, Taqsimot

pytestmark = pytest.mark.django_db


def _sorovlar(client, filial_yarat, foydalanuvchi, admin, revizor, n, boshlanish):
    for i in range(boshlanish, boshlanish + n):
        f = filial_yarat(f"M{i}")
        av = AV.objects.create(ref_1c=uuid.uuid4(), kod=f"m{i}", nomi=f"AV {i}", inv_raqam=f"M{i}", filial_rekvizit=f)
        AVQoldiq.objects.create(av=av, filial=f, soni=Decimal("1"), summa=Decimal("10"))
        Taqsimot.objects.create(av=av, filial=f, holat=Holat.ISHLATILMOQDA, soni=Decimal("1"))
        qayd_qosh(reviziya_och(f, None, [revizor], [], admin), None, admin, av=av)
    with CaptureQueriesContext(connection) as q:
        javob = client.get(reverse("reviziya:mobil"))
    assert javob.status_code == 200
    return len(q)


def test_mobil_royxat_sorovlari_reviziya_soniga_bogliq_emas(client_rol, filial_yarat, foydalanuvchi):
    admin, revizor = foydalanuvchi("admin"), foydalanuvchi("revizor")
    client = client_rol("admin")
    oz = _sorovlar(client, filial_yarat, foydalanuvchi, admin, revizor, 3, 0)
    kop = _sorovlar(client, filial_yarat, foydalanuvchi, admin, revizor, 12, 100)
    assert kop == oz


def test_progress_kop_progress_bilan_bir_xil(filial_yarat, foydalanuvchi):
    from reviziya.servis import progress, progress_kop

    admin, revizor = foydalanuvchi("admin"), foydalanuvchi("revizor")
    f = filial_yarat("P")
    rvlar = []
    for i in range(3):
        av = AV.objects.create(ref_1c=uuid.uuid4(), kod=f"p{i}", nomi=f"AV {i}", inv_raqam=f"P{i}", filial_rekvizit=f)
        AVQoldiq.objects.create(av=av, filial=f, soni=Decimal("2"), summa=Decimal("10"))
        Taqsimot.objects.create(av=av, filial=f, holat=Holat.ISHLATILMOQDA, soni=Decimal("2"))
        rvlar.append(av)
    rv = reviziya_och(f, None, [revizor], [], admin)
    qayd_qosh(rv, None, admin, av=rvlar[0])
    qayd_qosh(rv, None, admin, av=rvlar[1], soni=Decimal("5"))
    assert progress_kop([rv]) == {rv.pk: progress(rv)}
