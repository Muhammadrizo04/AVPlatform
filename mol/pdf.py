"""МОЛ aktini PDF'ga chiqarish (WeasyPrint)."""
from decimal import ROUND_HALF_UP, Decimal

from django.template.loader import render_to_string

from vositalar.models import Holat, Sozlama

from .sorovlar import akt_narxlari

TIYIN = Decimal("0.01")


def akt_pdf(akt) -> bytes:
    from weasyprint import HTML  # kech import: Pango faqat PDF kerak bo'lganda yuklanadi

    qatorlar = list(akt.qatorlar.select_related("av", "bolim", "filial").order_by("pk"))
    narxlar = akt_narxlari(akt, qatorlar)  # tasdiqlangan akt — saqlangan narx, qoralama — joriy
    holatlar = dict(Holat.choices)
    satrlar, jami = [], Decimal("0")
    for tartib, q in enumerate(qatorlar, start=1):
        av = q.av
        qiymat = (q.soni * narxlar[q.pk]).quantize(TIYIN, ROUND_HALF_UP)
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
