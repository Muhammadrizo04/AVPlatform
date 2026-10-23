"""Reviziyaning bo'limlar (xonalar) kesimi — mobil «Xonani tanlang» ro'yxati va panel jadvali uchun bitta manba."""
from decimal import Decimal

from django.db.models import Sum

from vositalar.bolimlar import daraxt

from .servis import qamrov_bolim_idlari

NOL = Decimal("0")
BOLIMSIZ_QIYMATI = "0"  # so'rovlardagi «bo'limsiz» qiymati (mobil `?bolim=0`)


def xonalar_kesimi(rv) -> list[dict]:
    """Qamrovdagi bo'limlar daraxt tartibida (+ oxirida bo'limsiz): `qiymat`, `bolim_id`, `nomi`, `toliq`,
    `chuqurlik`, `kutilgan`, `belgilangan` (dona), `tugadi` (ReviziyaXona yoki None). Nofaol bo'lim faqat unda
    kutilgan yoki belgilangan bo'lsa chiqadi."""
    kutilgan = dict(rv.kutilganlar.order_by().values_list("bolim_id").annotate(s=Sum("soni")))
    belgilangan = dict(
        rv.qaydlar.filter(av__isnull=False).order_by().values_list("bolim_id").annotate(s=Sum("soni"))
    )
    tugagan = {x.bolim_id: x for x in rv.tugagan_xonalar.select_related("tugatdi")}
    qamrov = qamrov_bolim_idlari(rv)

    def qator(bolim_id, qiymat, nomi, toliq, chuqurlik):
        return {
            "qiymat": qiymat, "bolim_id": bolim_id, "nomi": nomi, "toliq": toliq, "chuqurlik": chuqurlik,
            "kutilgan": kutilgan.get(bolim_id, NOL), "belgilangan": belgilangan.get(bolim_id, NOL),
            "tugadi": tugagan.get(bolim_id),
        }

    qatorlar = [
        qator(b.pk, str(b.pk), b.nomi, toliq, chuqurlik)
        for b, chuqurlik, toliq in daraxt(rv.filial_id)
        if (qamrov is None or b.pk in qamrov) and (b.faol or b.pk in kutilgan or b.pk in belgilangan)
    ]
    qatorlar.append(qator(None, BOLIMSIZ_QIYMATI, "Bo'limsiz", "Bo'limsiz / umumiy joy", 0))
    return qatorlar
