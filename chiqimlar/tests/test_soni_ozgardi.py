"""Tasdiqdan keyin 1C'da chiqim soni o'zgarsa — belgi va tuzatish; kartochka farqi kutilayotgan chiqimni hisobga oladi."""
import uuid
from datetime import timedelta
from decimal import Decimal as D

import pytest
from django.urls import reverse
from django.utils import timezone

from chiqimlar.models import ChiqimHujjat
from chiqimlar.servis import chiqim_tarixi, chiqimlarni_yangila, tasdiqla, tasdiqni_qaytar
from onec.models import AVQoldiq, Harakat1C
from panel.vazifalar import kutayotgan_ishlar
from vositalar.amallar import farq
from vositalar.models import Bolim, Sozlama, Taqsimot
from vositalar.moslash import moslashtir
from vositalar.tests.test_bayroqlar import av_yarat, qator
from vositalar.views import _joylashuv, _taqsimot_kontekst

pytestmark = pytest.mark.django_db


@pytest.fixture
def f(filial_yarat):
    return filial_yarat("07")


@pytest.fixture
def his(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def muhit(f, his):
    """10 dona, 3 tasi chiqim bilan tasdiqlangan: 1C va taqsimot 7 da. (chiqim, 1C harakati, AV, bo'lim)."""
    Sozlama.objects.filter(pk=Sozlama.PK).update(chiqim_boshlanishi=timezone.now() - timedelta(days=30))
    b = Bolim.objects.create(filial=f, nomi="A")
    av = av_yarat(f, soni="7")
    t = qator(av, f, "10", bolim=b)
    h = Harakat1C.objects.create(
        sana=timezone.now() - timedelta(days=1), hujjat_turi="РеализацияОС", hujjat_raqami="1", hujjat_ref=uuid.uuid4(),
        av=av, filial=f, vid="chiqim", soni=D("3"), summa=D("9"),
    )
    yangila()
    c = ChiqimHujjat.objects.get(hujjat_ref=h.hujjat_ref)
    tasdiqla(c, "sotildi", {t.pk: D("3")}, his, kutilgan_soni=D("3"))
    return c, h, av, b


def yangila():
    return chiqimlarni_yangila(timezone.now() - timedelta(days=5), timezone.now() + timedelta(days=5))


def soni_ozgardi(c, h, yangi):
    """1C'da hujjat tuzatildi: qoldiq ham shunga o'zgaradi."""
    Harakat1C.objects.filter(pk=h.pk).update(soni=D(yangi))
    AVQoldiq.objects.filter(av=c.av, filial=c.filial).update(soni=D("10") - D(yangi))
    stat = yangila()
    moslashtir()
    c.refresh_from_db()
    return stat


def test_son_ozgarsa_belgilanadi_tasdiq_ozgarmaydi(muhit):
    c, h, *_ = muhit

    stat = soni_ozgardi(c, h, "1")

    assert stat["ozgardi"] == 1
    assert (c.soni, c.ozgargan_soni, c.holat) == (D("3"), D("1"), "tasdiqlangan")


def test_son_ozgarmasa_belgi_yoq(muhit):
    c, *_ = muhit

    assert yangila()["ozgardi"] == 0
    c.refresh_from_db()
    assert c.ozgargan_soni is None


def test_1c_da_son_qaytsa_belgi_olinadi(muhit):
    c, h, *_ = muhit
    soni_ozgardi(c, h, "1")

    soni_ozgardi(c, h, "3")

    assert c.ozgargan_soni is None


@pytest.mark.parametrize("yangi", ["1", "5"])
def test_tasdiq_bekor_qilinsa_yangi_son_bilan_kutadi(muhit, his, yangi):
    c, h, av, _ = muhit
    soni_ozgardi(c, h, yangi)

    assert tasdiqni_qaytar(c, his) == "kutilmoqda"

    c.refresh_from_db()
    assert (c.soni, c.ozgargan_soni) == (D(yangi), None)
    moslashtir()
    assert farq(av, c.filial) == 0  # 1C qoldig'i + K = taqsimot


def test_vazifa_royxat_va_sahifada_korinadi(muhit, his, client_rol):
    c, h, *_ = muhit
    soni_ozgardi(c, h, "1")

    [ish] = [i for i in kutayotgan_ishlar(his) if i["kalit"] == "chiqim_ozgargan"]
    assert ish["soni"] == 1

    kirgan = client_rol("hisobchi")
    javob = kirgan.get(reverse("chiqimlar:royxat"), {"holat": "tasdiqlangan", "ozgargan": "1"})
    assert [x.pk for x in javob.context["sahifa"]] == [c.pk]
    assert "1C&#x27;da soni o&#x27;zgargan" in javob.content.decode() or "1C'da soni o'zgargan" in javob.content.decode()
    html = kirgan.get(reverse("chiqimlar:tasdiqlash", args=[c.pk])).content.decode()
    assert "1C'da soni o'zgargan" in html
    assert any("1C'da soni o'zgardi" in t["matn"] for t in chiqim_tarixi(c))


def kutilayotgan_chiqim(f):
    av = av_yarat(f, soni="3")
    qator(av, f, "5")
    ChiqimHujjat.objects.create(
        hujjat_turi="РеализацияОС", hujjat_raqami="1", hujjat_ref=uuid.uuid4(), sana=timezone.now(), av=av, filial=f,
        soni=D("2"), summa=D("1"), taxmin_tur="sotildi",
    )
    return av


def test_kartochka_farqi_moslash_bilan_bir_xil(f, his):
    av = kutilayotgan_chiqim(f)

    [g] = _taqsimot_kontekst(his, av)["taqsimot_guruhlari"]

    assert (g["farq"], g["kutilmoqda"]) == (farq(av, f), D("2")) == (0, D("2"))
    assert _joylashuv([g])["kutilmoqda"] == D("2")


def test_kartochkada_moslash_tugmasi_chiqmaydi(f, client_rol):
    av = kutilayotgan_chiqim(f)

    html = client_rol("hisobchi").get(reverse("vositalar:kartochka", args=[av.pk])).content.decode()

    assert ">Moslash<" not in html and "chiqimi tasdiq kutmoqda" in html
    assert Taqsimot.objects.get(av=av).soni == D("5")


def test_haqiqiy_ortiqcha_farq_qoladi(f, his):
    av = av_yarat(f, soni="3")
    qator(av, f, "5")

    [g] = _taqsimot_kontekst(his, av)["taqsimot_guruhlari"]

    assert g["farq"] == D("-2") == farq(av, f)
