"""Sinxron taqsimotni noto'g'ri 1C javobi yoki ko'rinmagan hujjat tufayli o'chirmasligi."""
import uuid
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from chiqimlar.models import ChiqimHujjat
from onec.models import AV, AVQoldiq, SinxronJurnal
from onec.sinxron import sinxronla
from onec.tests.test_sinxron import SoxtaClient, namuna_harakat
from vositalar.models import Bolim, Sozlama, Taqsimot
from vositalar.moslash import moslashtir

pytestmark = pytest.mark.django_db
OK, XATO = SinxronJurnal.Natija.OK, SinxronJurnal.Natija.XATO


@pytest.fixture
def muhit():
    """(mijoz, taqsimot qatori, bo'lim): to'liq sinxrondan keyin bitta qator xonaga joylangan."""
    c = SoxtaClient()
    assert sinxronla(c, toliq=True).natija == OK
    t = Taqsimot.objects.filter(soni__gt=0).order_by("pk").first()
    b = Bolim.objects.create(filial=t.filial, nomi="A xona")
    Taqsimot.objects.filter(pk=t.pk).update(bolim=b)
    t.refresh_from_db()
    return c, t, b


def rasm():
    """Taqsimot va qoldiqning hozirgi holati: himoya ishlaganda ular o'zgarmasligi kerak."""
    return (
        sorted(Taqsimot.objects.values_list("pk", "soni", "bolim_id")),
        sorted(AVQoldiq.objects.values_list("av_id", "filial_id", "soni")),
    )


def test_bosh_qoldiqlar_sinxronni_toxtatadi(muhit):
    c, _, _ = muhit
    oldin = rasm()
    c.vos["qoldiqlar"] = []

    jurnal = sinxronla(c)

    assert jurnal.natija == XATO and "qoldiq" in jurnal.xato_matni
    assert rasm() == oldin


def test_bosh_vositalar_sinxronni_toxtatadi(muhit):
    c, _, _ = muhit
    oldin = rasm()
    c.vos["vositalar"] = []

    assert sinxronla(c).natija == XATO
    assert rasm() == oldin
    assert not AV.objects.filter(onec_da_yoq=True).exists()


def test_keskin_kamaygan_qoldiqlar_sinxronni_toxtatadi(muhit, monkeypatch):
    monkeypatch.setattr("onec.sinxron.KICHIK_BAZA", 1)
    c, _, _ = muhit
    oldin = rasm()
    c.vos["qoldiqlar"] = c.vos["qoldiqlar"][: len(c.vos["qoldiqlar"]) // 2]

    assert sinxronla(c).natija == XATO
    assert rasm() == oldin


def test_oddiy_kamayish_toxtatmaydi(muhit, monkeypatch):
    monkeypatch.setattr("onec.sinxron.KICHIK_BAZA", 1)
    c, _, _ = muhit
    c.vos["qoldiqlar"] = c.vos["qoldiqlar"][1:]

    assert sinxronla(c).natija == OK


def test_taqsimoti_bor_filial_yoqolsa_sinxron_toxtaydi(muhit):
    c, t, _ = muhit
    oldin = rasm()
    c.sprav["filiallar"] = [f for f in c.sprav["filiallar"] if f["ref"] != str(t.filial.ref_1c)]

    jurnal = sinxronla(c)

    assert jurnal.natija == XATO and t.filial.nomi in jurnal.xato_matni
    assert rasm() == oldin


def test_majburiy_sinxron_himoyani_chetlab_otadi(muhit):
    c, _, _ = muhit
    c.vos["qoldiqlar"] = []

    assert sinxronla(c, toliq=True, majburiy=True).natija == OK
    assert not Taqsimot.objects.exists()


def test_buyruq_majburiy_bayrogi(muhit, monkeypatch):
    c, _, _ = muhit
    c.vos["qoldiqlar"] = []
    monkeypatch.setattr("onec.management.commands.sinxron.OneCClient.settingsdan", lambda: c)

    with pytest.raises(CommandError):
        call_command("sinxron", stdout=StringIO())
    call_command("sinxron", "--toliq", "--majburiy", stdout=StringIO())

    assert not Taqsimot.objects.exists()


def chiqim_oynadan_tashqarida(c, t):
    """1C: AV 60 kun oldingi sana bilan chiqib ketgan — qoldiq yo'q, hujjat 45 kunlik oynadan tashqarida."""
    av_ref, filial_ref = str(t.av.ref_1c), str(t.filial.ref_1c)
    c.vos["qoldiqlar"] = [q for q in c.vos["qoldiqlar"] if (q["av"], q["filial"]) != (av_ref, filial_ref)]
    ref = str(uuid.uuid4())
    h = namuna_harakat(c, timezone.now() - timedelta(days=60))
    h.update(av=av_ref, filial=filial_ref, vid="chiqim", soni=float(t.soni), summa=1, hujjat_ref=ref)
    c.har.append(h)
    return ref


def toza_muhit(muhit):
    """Namunadagi chiqimlar aralashmasin; chiqim hisobi 90 kun oldindan boshlanadi."""
    c, _, b = muhit
    c.har = [x for x in c.har if x["vid"] != "chiqim"]
    Sozlama.objects.filter(pk=Sozlama.PK).update(chiqim_boshlanishi=timezone.now() - timedelta(days=90))
    assert sinxronla(c, toliq=True).natija == OK
    return c, Taqsimot.objects.select_related("av", "filial").get(bolim=b), b


def test_eski_sanali_chiqim_joyni_ochirmaydi(muhit):
    c, t, b = toza_muhit(muhit)
    ref = chiqim_oynadan_tashqarida(c, t)

    jurnal = sinxronla(c)  # soatlik: hujjat ko'rinmaydi, qoldiq 0

    assert jurnal.natija == OK
    assert jurnal.ozgarishlar["moslash"]["kechiktirildi"] == 1
    assert Taqsimot.objects.filter(pk=t.pk, bolim=b).exists()

    assert sinxronla(c, toliq=True).natija == OK  # tungi: hujjat ko'rindi, tasdiq kutadi

    assert ChiqimHujjat.objects.filter(hujjat_ref=ref, holat="kutilmoqda").exists()
    assert Taqsimot.objects.filter(pk=t.pk, bolim=b).exists()


def test_hujjatsiz_nolga_tushgan_av_tolik_sinxronda_ochadi(muhit):
    c, t, _ = toza_muhit(muhit)
    c.vos["qoldiqlar"] = [
        q for q in c.vos["qoldiqlar"] if (q["av"], q["filial"]) != (str(t.av.ref_1c), str(t.filial.ref_1c))
    ]

    sinxronla(c)
    assert Taqsimot.objects.filter(pk=t.pk).exists()

    sinxronla(c, toliq=True)
    assert not Taqsimot.objects.filter(pk=t.pk).exists()


def test_kechiktirilgan_qator_invariantni_buzmaydi(muhit):
    _, t, _ = muhit
    AVQoldiq.objects.filter(av=t.av, filial=t.filial).delete()

    natija = moslashtir(toliq=False)

    assert natija["nolga_tushdi"] == 0 and natija["kechiktirildi"] == 1
