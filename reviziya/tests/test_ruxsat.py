"""`reviziya.ruxsat`: `ozgartira_oladi` (bitta reviziya) va `ozgartiradigan_shart` (queryset) bir xil natija berishi."""
import pytest

from reviziya.models import Reviziya
from reviziya.ruxsat import ozgartira_oladi, ozgartiradigan_shart
from reviziya.servis import reviziya_och
from vositalar.models import Bolim, Sozlama
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db


@pytest.fixture
def rv_va_rollar(filial_yarat, foydalanuvchi):
    fa = filial_yarat("A")
    qator(av_yarat(fa, inv="INV-1"), fa, "1", bolim=Bolim.objects.create(filial=fa, nomi="X"))
    ochgan, revizor = foydalanuvchi("hisobchi"), foydalanuvchi("revizor")
    rv = reviziya_och(fa, None, [revizor], [{"ism": "K", "lavozim": "R"}], ochgan)
    return rv, {
        "ochgan": ochgan,
        "revizor": revizor,
        "boshqa_hisobchi": foydalanuvchi("hisobchi"),
        "boshqa_revizor": foydalanuvchi("revizor"),
        "admin": foydalanuvchi("admin"),
        "hr": foydalanuvchi("hr"),
    }


def _ikkalasi(user, rv):
    """Funksiya va queryset sharti mos kelishini tekshirib, natijani qaytaradi."""
    funksiya = ozgartira_oladi(user, rv)
    queryset = Reviziya.objects.filter(ozgartiradigan_shart(user), pk=rv.pk).distinct().exists()
    assert funksiya == queryset
    return funksiya


def test_standart_boshqaruvchilar_va_biriktirilgan_revizor(rv_va_rollar):
    rv, r = rv_va_rollar
    kutilgan = {"ochgan": True, "revizor": True, "boshqa_hisobchi": True, "boshqa_revizor": True,
                "admin": True, "hr": False}
    # boshqa_revizor: reviziya_boshqarish huquqi bor (REVIZOR roli) -> filial cheklovi chaqiruvchida
    assert {nom: _ikkalasi(u, rv) for nom, u in r.items()} == kutilgan


def test_faqat_ozimniki_yoqilsa(rv_va_rollar):
    rv, r = rv_va_rollar
    Sozlama.objects.filter(pk=Sozlama.PK).update(reviziya_faqat_ozimniki=True)
    kutilgan = {"ochgan": True, "revizor": True, "boshqa_hisobchi": False, "boshqa_revizor": False,
                "admin": True, "hr": False}
    assert {nom: _ikkalasi(u, rv) for nom, u in r.items()} == kutilgan
