"""Reviziya dalolatnomasi PDF'ga (WeasyPrint, `mol/pdf.py` uslubida)."""
from decimal import ROUND_HALF_UP, Decimal

from django.template.loader import render_to_string

from onec.models import Xodim
from panel.logotip import logotip_uri
from vositalar.models import Holat, Sozlama
from vositalar.narx import filial_narxlari

from .servis import KOMISSIYA_RAIS
from .solishtir import (
    GURUH_NOMLARI, GURUHLAR, bolim_boyicha, bolim_kesim_nomi, bolim_nomlari, guruh_nomi, jamlar, solishtir,
)

TIYIN = Decimal("0.01")
KAMOMAD = ("kam", "topilmadi")


def _narxlar(reviziya, qatorlar) -> dict[int, Decimal]:
    """Kamomad qatorlaridagi AV'larning reviziya ochilgandagi dona narxi; eski reviziyada — filialdagi joriy narx."""
    idlar = {q.av_id for q in qatorlar if q.guruh in KAMOMAD}
    saqlangan = dict(reviziya.kutilganlar.filter(av_id__in=idlar, dona_narxi__isnull=False).values_list("av_id", "dona_narxi"))
    narx = filial_narxlari(idlar - saqlangan.keys())
    return {av_id: saqlangan[av_id] if av_id in saqlangan else narx(av_id, reviziya.filial_id) for av_id in idlar}


def mollar(reviziya, bolim: str = ""):
    """Qamrovdagi (reviziya ochilgandagi suratdagi) МОЛlar — dalolatnomada imzo qatori uchun; `bolim` (id yoki
    "bolimsiz") berilsa — faqat shu bo'limda kutilganlar."""
    kutilganlar = reviziya.kutilganlar.exclude(mol=None)
    if bolim == "bolimsiz":
        kutilganlar = kutilganlar.filter(bolim=None)
    elif bolim.isdigit():
        kutilganlar = kutilganlar.filter(bolim_id=int(bolim))
    return Xodim.objects.filter(pk__in=kutilganlar.values("mol")).order_by("ism")


def dalolatnoma_pdf(reviziya, pul: bool = False, bolim: str = "") -> bytes:
    """`pul=False` — «AV qiymati» ustuni va jami chiqmaydi (`pul_korish` huquqi yo'q). `bolim` (id yoki "bolimsiz")
    — faqat shu bo'lim kesimi (`bolim_boyicha`)."""
    from weasyprint import HTML  # kech import: Pango faqat PDF kerak bo'lganda yuklanadi

    qatorlar = bolim_boyicha(solishtir(reviziya), bolim)
    nomlar = bolim_nomlari(reviziya.filial_id)
    holatlar = dict(Holat.choices)
    narxlar = _narxlar(reviziya, qatorlar) if pul else {}
    jami_qiymat = Decimal("0")
    farqlar = []
    for q in qatorlar:
        if q.guruh == "topildi":
            continue
        qiymat = None
        if pul and q.guruh in KAMOMAD:
            qiymat = (abs(q.farq) * narxlar.get(q.av_id, Decimal("0"))).quantize(TIYIN, ROUND_HALF_UP)
            jami_qiymat += qiymat
        farqlar.append({
            "guruh": guruh_nomi(q),
            "inv": q.inv,
            "nomi": q.av_nomi or q.qr_matn,
            "bolim": q.bolim_nomi,
            "nishon_bolim": "" if q.nishon_bolim_id is None else nomlar.get(q.nishon_bolim_id, ""),
            "holat": holatlar.get(q.holat, q.holat),
            "nishon_holat": holatlar.get(q.nishon_holat, q.nishon_holat),
            "kutilgan": q.kutilgan,
            "topilgan": q.topilgan,
            "farq": q.farq,
            "qiymat": qiymat,
        })
    jami = jamlar(qatorlar)
    html = render_to_string("reviziya/dalolatnoma_pdf.html", {
        "rv": reviziya,
        "kompaniya": Sozlama.ol().kompaniya_nomi,
        "logotip": logotip_uri(),
        "jamlar": [(GURUH_NOMLARI[g], jami[g]) for g in reversed(GURUHLAR)],
        "farqlar": farqlar,
        "jami_qiymat": jami_qiymat,
        "revizorlar": reviziya.revizorlar.order_by("first_name", "username"),
        "rais": [a for a in reviziya.komissiya if a.get("rol") == KOMISSIYA_RAIS],
        "azolar": [a for a in reviziya.komissiya if a.get("rol") != KOMISSIYA_RAIS],
        "mollar": mollar(reviziya, bolim),
        "kesim_nomi": bolim_kesim_nomi(bolim, nomlar),
        "pul_huquqi": pul,
    })
    return HTML(string=html).write_pdf()
