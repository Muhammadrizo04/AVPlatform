"""МОЛ aktini PDF'ga chiqarish (WeasyPrint)."""
from decimal import ROUND_HALF_UP, Decimal

from django.template.loader import render_to_string

from onec.models import AV
from vositalar.amortizatsiya import dona_narxi
from vositalar.models import Holat, Sozlama

TIYIN = Decimal("0.01")


def akt_pdf(akt) -> bytes:
    from weasyprint import HTML  # kech import: Pango faqat PDF kerak bo'lganda yuklanadi

    qatorlar = list(akt.qatorlar.select_related("av", "bolim", "filial").order_by("pk"))
    avlar = {a.pk: a for a in AV.objects.qoldiq_bilan().filter(pk__in={q.av_id for q in qatorlar})}
    holatlar = dict(Holat.choices)
    satrlar, jami = [], Decimal("0")
    for tartib, q in enumerate(qatorlar, start=1):
        av = avlar[q.av_id]
        qiymat = (q.soni * dona_narxi(av.jami_summa, av.jami_soni)).quantize(TIYIN, ROUND_HALF_UP)
        jami += qiymat
        satrlar.append(
            {
                "tartib": tartib,
                "inv": av.inv_raqam,
                "nomi": av.nomi,
                "bolim": q.bolim.toliq_nomi if q.bolim else "—",
                "holat": holatlar.get(q.holat, q.holat),
                "soni": f"{q.soni.normalize():f}",
                "qiymat": f"{qiymat:.2f}",
            }
        )
    html = render_to_string(
        "mol/akt_pdf.html",
        {
            "akt": akt,
            "kompaniya": Sozlama.ol().kompaniya_nomi,
            "satrlar": satrlar,
            "jami": f"{jami:.2f}",
        },
    )
    return HTML(string=html).write_pdf()
