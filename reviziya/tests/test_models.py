import uuid

import pytest
from django.db import IntegrityError, transaction

from onec.models import AV
from reviziya.models import Reviziya, ReviziyaQayd


@pytest.fixture
def reviziya(foydalanuvchi, filial_yarat):
    return Reviziya.objects.create(raqam=7, filial=filial_yarat("A"), ochdi=foydalanuvchi("hisobchi"))


def test_nomi_formati(reviziya):
    assert reviziya.nomi == "RV-000007"


@pytest.mark.parametrize("bolimli", [True, False])
def test_qayd_noyobligi(reviziya, foydalanuvchi, bolimli):
    from vositalar.models import Bolim

    av = AV.objects.create(ref_1c=uuid.uuid4(), kod="1", nomi="Stol")
    bolim = Bolim.objects.create(filial=reviziya.filial, nomi="Ombor") if bolimli else None
    kim = foydalanuvchi("revizor")
    kw = dict(reviziya=reviziya, bolim=bolim, av=av, holat="ishlatilmoqda", qr_matn="", soni=1, usul="qidiruv", kim=kim)
    ReviziyaQayd.objects.create(**kw)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviziyaQayd.objects.create(**kw)
