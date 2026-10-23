"""Reviziyaning bo'limlar kesimi: «xona tugadi» belgisi, panel jadvali, bo'lim bo'yicha Excel va dalolatnoma."""
import io
import uuid

import pytest
from django.urls import reverse
from openpyxl import load_workbook
from pypdf import PdfReader

from onec.models import Xodim
from reviziya.models import ReviziyaXona
from reviziya.servis import qayd_qosh, reviziya_och, yakunla
from vositalar.models import Bolim
from vositalar.tests.test_bayroqlar import av_yarat, qator

from .test_mobil import kirgan, matn

pytestmark = pytest.mark.django_db


@pytest.fixture
def muhit(filial_yarat, foydalanuvchi):
    """Ikki xona: «Kabinet» (stol, МОЛ Aliyev) va «Ombor» (stul, МОЛ Boboyev); butun filial reviziyasi."""
    fa = filial_yarat("07")
    revizor, hisobchi = foydalanuvchi("revizor"), foydalanuvchi("hisobchi")
    kabinet, ombor = Bolim.objects.create(filial=fa, nomi="Kabinet"), Bolim.objects.create(filial=fa, nomi="Ombor")
    ali = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Aliyev", filial=fa)
    bobo = Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Boboyev", filial=fa)
    stol, stul = av_yarat(fa, inv="INV-STOL"), av_yarat(fa, inv="INV-STUL")
    qator(stol, fa, "1", bolim=kabinet, mol=ali)
    qator(stul, fa, "1", bolim=ombor, mol=bobo)
    rv = reviziya_och(fa, None, [revizor], [], hisobchi)
    qayd_qosh(rv, kabinet, revizor, av=stol)
    return rv, kabinet, ombor, revizor, hisobchi


def test_xona_tugadi_belgisi(muhit, foydalanuvchi):
    rv, kabinet, ombor, revizor, hisobchi = muhit
    manzil = reverse("reviziya:mobil_xona_tugadi", args=[rv.pk])
    c = kirgan(revizor)

    assert c.post(manzil, {"bolim": kabinet.pk, "tugadi": "1"}).status_code == 302
    assert c.post(manzil, {"bolim": kabinet.pk, "tugadi": "1"}).status_code == 302  # takror — bitta yozuv
    x = ReviziyaXona.objects.get()
    assert (x.bolim, x.tugatdi) == (kabinet, revizor)
    assert "✓ tugadi" in matn(c.get(reverse("reviziya:mobil_xonalar", args=[rv.pk])))
    assert "Xonani qayta ochish" in matn(c.get(reverse("reviziya:mobil_skan", args=[rv.pk]) + f"?bolim={kabinet.pk}"))

    c.post(manzil, {"bolim": 0, "tugadi": "1"})  # bo'limsiz
    assert ReviziyaXona.objects.filter(bolim=None).exists()
    c.post(manzil, {"bolim": kabinet.pk, "tugadi": "0"})
    assert not ReviziyaXona.objects.filter(bolim=kabinet).exists()

    # biriktirilmagan revizor — 404; GET — 405; yakunlangan — 403
    assert kirgan(foydalanuvchi("revizor")).post(manzil, {"bolim": kabinet.pk, "tugadi": "1"}).status_code == 404
    assert c.get(manzil).status_code == 405
    yakunla(rv, hisobchi)
    assert c.post(manzil, {"bolim": ombor.pk, "tugadi": "1"}).status_code == 403


def test_panel_kesim_jadvali(muhit):
    rv, kabinet, ombor, revizor, hisobchi = muhit
    ReviziyaXona.objects.create(reviziya=rv, bolim=kabinet, tugatdi=revizor)
    javob = kirgan(hisobchi).get(reverse("reviziya:sahifa", args=[rv.pk]))
    kesim = {x["nomi"]: x for x in javob.context["kesim"]}

    assert set(kesim) == {"Kabinet", "Ombor"}  # bo'sh «Bo'limsiz» chiqmaydi
    assert (kesim["Kabinet"]["belgilangan"], kesim["Kabinet"]["kamomad"], kesim["Kabinet"]["tugadi"].tugatdi) == (
        1, 0, revizor,
    )
    assert (kesim["Ombor"]["belgilangan"], kesim["Ombor"]["kamomad"], kesim["Ombor"]["tugadi"]) == (0, 1, None)
    html = matn(javob)
    assert "Bo'limlar kesimi" in html and "Tugadi" in html and "Boshlanmagan" in html
    assert f'{reverse("reviziya:pdf", args=[rv.pk])}?bolim={ombor.pk}' in html


def test_bolim_boyicha_excel_va_dalolatnoma(muhit):
    rv, kabinet, ombor, revizor, hisobchi = muhit
    c = kirgan(hisobchi)

    r = c.get(reverse("reviziya:excel", args=[rv.pk]), {"bolim": ombor.pk})
    satrlar = list(load_workbook(io.BytesIO(r.content)).active.values)[1:]
    assert [s[1] for s in satrlar] == ["INV-STUL"]
    assert "Ombor" in r["Content-Disposition"]

    r = c.get(reverse("reviziya:pdf", args=[rv.pk]), {"bolim": ombor.pk})
    pdf = "".join(s.extract_text() for s in PdfReader(io.BytesIO(r.content)).pages)
    assert "Bo'lim kesimi: Ombor" in pdf and "INV-STUL" in pdf and "INV-STOL" not in pdf
    assert "Boboyev" in pdf and "Aliyev" not in pdf  # faqat shu bo'lim МОЛ'i

    # filtrsiz — butun reviziya
    pdf = "".join(s.extract_text() for s in PdfReader(io.BytesIO(c.get(reverse("reviziya:pdf", args=[rv.pk])).content)).pages)
    assert "Bo'lim kesimi" not in pdf and "Aliyev" in pdf and "Boboyev" in pdf
