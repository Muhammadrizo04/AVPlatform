"""«Kutayotgan ishlar» (tepadagi qo'ng'iroqcha): rol va filial cheklovi bilan, ish bajarilgach yo'qoladi."""
import uuid

import pytest
from django.urls import reverse

from mol.models import MolAkt
from mol.servis import akt_bekor_qil, qoralamaga_qosh
from onec.models import Xodim
from panel.vazifalar import kutayotgan_ishlar
from reviziya.servis import reviziya_och
from reviziya.tests.test_mobil import kirgan, matn
from vositalar.models import Bolim, Taqsimot
from vositalar.tests.test_bayroqlar import av_yarat, qator

pytestmark = pytest.mark.django_db


@pytest.fixture
def muhit(filial_yarat, foydalanuvchi):
    """`fa` filialida revizor biriktirgan (javobgarsiz -> kassir) qoralama akt va ochiq reviziya."""
    fa = filial_yarat("07")
    revizor, hisobchi = foydalanuvchi("revizor", filiallar=[fa]), foydalanuvchi("hisobchi", filiallar=[fa])
    xona = Bolim.objects.create(filial=fa, nomi="Kabinet")
    qator(av_yarat(fa, inv="INV-1"), fa, "1", bolim=xona)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    kassir = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Kassir", filial=fa)
    akt, _ = qoralamaga_qosh(None, kassir, [(t, t.soni) for t in Taqsimot.objects.all()], revizor, rv.akt_izohi)
    return fa, rv, akt, revizor, hisobchi


def nomlar(user) -> dict[str, int]:
    return {i["nomi"]: i["soni"] for i in kutayotgan_ishlar(user)}


def test_hisobchiga_qoralama_akt_revizorga_reviziya(muhit, foydalanuvchi, filial_yarat):
    fa, rv, akt, revizor, hisobchi = muhit
    assert nomlar(hisobchi) == {"Topshirish akti tasdiq kutmoqda": 1}
    # revizor aktni tasdiqlay olmaydi — unga faqat o'zi revizor bo'lgan ochiq reviziya
    assert nomlar(revizor) == {"Siz revizor bo'lgan ochiq reviziya": 1}
    # boshqa filial hisobchisi bu aktni ko'rmaydi
    assert nomlar(foydalanuvchi("hisobchi", filiallar=[filial_yarat("99")])) == {}
    # rahbarda akt tasdiqlash huquqi yo'q
    assert nomlar(foydalanuvchi("rahbar")) == {}


def test_bajarilgach_yoqoladi(muhit):
    fa, rv, akt, revizor, hisobchi = muhit
    akt_bekor_qil(akt, hisobchi)
    assert nomlar(hisobchi) == {}


def test_qongiroqcha_va_menyu_belgisi(muhit):
    fa, rv, akt, revizor, hisobchi = muhit
    html = matn(kirgan(hisobchi).get(reverse("vositalar:royxat")))
    assert 'class="av-qongiroq-son">1<' in html
    assert f'{reverse("mol:akt_royxat")}?holat=qoralama' in html and "Topshirish akti tasdiq kutmoqda" in html
    assert 'title="Tasdiq kutayotgan qoralama aktlar">1<' in html


def test_ish_yoq_bolsa_bosh_matn(foydalanuvchi):
    html = matn(kirgan(foydalanuvchi("hisobchi")).get(reverse("vositalar:royxat")))
    assert "Hozircha kutayotgan ish yo'q." in html and "av-qongiroq-son" not in html


def test_reviziya_sahifasida_aktlar(muhit, foydalanuvchi, filial_yarat):
    fa, rv, akt, revizor, hisobchi = muhit
    html = matn(kirgan(hisobchi).get(reverse("reviziya:sahifa", args=[rv.pk])))
    assert "Javobgar shaxsga biriktirish aktlari" in html
    assert reverse("mol:akt", args=[akt.pk]) in html and "Javobgarsiz" in html and "Kassir" in html
    assert "xodim imzolagach tasdiqlang" in html
    # boshqa reviziya izohidagi akt bu yerda chiqmaydi
    akt.izoh = "boshqa"
    akt.save()
    assert "Javobgar shaxsga biriktirish aktlari" not in matn(kirgan(hisobchi).get(reverse("reviziya:sahifa", args=[rv.pk])))
    assert MolAkt.objects.count() == 1
