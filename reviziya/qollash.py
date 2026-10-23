"""Reviziya farqlarini taqsimotga qo'llash (spec §5.2) va reviziyani yopish.

`qolla` reviziya qatorini butun chaqiruv davomida `select_for_update` bilan qulflaydi (parallel qo'llashlar navbatga
turadi); har kalit alohida savepoint'da — bitta kalit xatosi boshqalarini bekor qilmaydi, kalit esa hech qachon
qisman qo'llanmaydi. Har kalit natijasi `ReviziyaQollash` jurnaliga yoziladi.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from onec.models import AV
from vositalar.amallar import AmalXato, holat_ozgartir, kochir
from vositalar.models import Bolim, Holat, Taqsimot, TaqsimotHarakat

from .models import Reviziya, ReviziyaQollash
from .servis import ReviziyaXato
from .solishtir import solishtir

NOL = Decimal("0")
QOLLANADI = ("boshqa_joyda", "holat_boshqa", "kam", "topilmadi")
REVIZIYA = TaqsimotHarakat.Sabab.REVIZIYA


def qollanadimi(q) -> bool:
    """Vedomost qatorini taqsimotga qo'llash mumkinmi: «Bo'limsiz» joyga ko'chirish qo'llanmaydi (xona noma'lum)."""
    return q.guruh in QOLLANADI and not (q.guruh == "boshqa_joyda" and q.nishon_bolim_id is None)


def _yakunlangan_qulfla(reviziya_id: int) -> Reviziya:
    reviziya = Reviziya.objects.select_for_update().get(pk=reviziya_id)
    if reviziya.holat != Reviziya.Holat.YAKUNLANGAN:
        raise ReviziyaXato("Reviziya yakunlanmagan yoki allaqachon yopilgan.")
    return reviziya


def qolla(reviziya: Reviziya, kalitlar: list[str], kim) -> list[ReviziyaQollash]:
    """Tanlangan vedomost qatorlarini (kalitlar) taqsimotga qo'llaydi; har kalit uchun jurnal yozuvi qaytadi."""
    natijalar = []
    with transaction.atomic():
        reviziya = _yakunlangan_qulfla(reviziya.pk)
        qatorlar = {q.kalit: q for q in solishtir(reviziya)}
        # Kerakli AV'larning barcha taqsimot qatorlari bitta so'rovda, global pk tartibida qulflanadi
        # (moslash, mol.servis, chiqimlar.servis bilan bir xil) — AV ma'lumotlari bo'yicha navbat bilan
        # qulflash deadlock'ga olib kelardi. Keyingi har-kalit qulflari allaqachon bizda.
        av_idlar = {qatorlar[k].av_id for k in kalitlar if k in qatorlar and qatorlar[k].guruh in QOLLANADI}
        if av_idlar:
            list(
                Taqsimot.objects.select_for_update()
                .filter(filial_id=reviziya.filial_id, av_id__in=av_idlar)
                .order_by("pk")
            )
        for kalit in kalitlar:
            natijalar.append(_kalit_qolla(reviziya, kalit, qatorlar.get(kalit), kim))
    return natijalar


def _kalit_qolla(reviziya, kalit, q, kim) -> ReviziyaQollash:
    jurnal = dict(reviziya=reviziya, kalit=kalit[:255], kim=kim)
    if q is None:
        return ReviziyaQollash.objects.create(guruh="", soni=NOL, natija="xato", xato="Qator topilmadi.", **jurnal)
    soni = abs(q.farq)
    jurnal.update(guruh=q.guruh, soni=soni)
    if ReviziyaQollash.objects.filter(reviziya=reviziya, kalit=kalit, natija=ReviziyaQollash.Natija.OK).exists():
        return ReviziyaQollash.objects.create(natija="xato", xato="Bu qator allaqachon qo'llangan.", **jurnal)
    if q.guruh not in QOLLANADI:
        return ReviziyaQollash.objects.create(natija="xato", xato="Bu qatorni qo'llab bo'lmaydi.", **jurnal)
    try:
        with transaction.atomic():
            _taqsimotga(reviziya, q, soni, kim)
            return ReviziyaQollash.objects.create(natija="ok", **jurnal)
    except (AmalXato, ReviziyaXato) as xato:
        return ReviziyaQollash.objects.create(natija="xato", xato=str(xato), **jurnal)


def _taqsimotga(reviziya, q, soni, kim) -> None:
    """Bitta vedomost qatorini joriy taqsimotga qo'llaydi; mos qatorlar (har xil МОЛ) pk tartibida sarflanadi."""
    # Qatorlar `qolla` da global pk tartibida (moslash/mol/chiqimlar bilan bir xil) allaqachon qulflangan;
    # bu yerdagi qayta qulflash hech narsa kutmaydi.
    if q.guruh == "boshqa_joyda" and q.nishon_bolim_id is None:
        raise ReviziyaXato("Bo'limsiz joyga ko'chirib bo'lmaydi — xonani aniqlang.")
    qulflangan = Taqsimot.objects.select_for_update().filter(av_id=q.av_id, filial_id=reviziya.filial_id)
    mos = [t for t in qulflangan.order_by("pk") if t.bolim_id == q.bolim_id and t.holat == q.holat]
    mavjud = sum((t.soni for t in mos), NOL)
    if mavjud < soni:
        nomi = AV.objects.filter(pk=q.av_id).values_list("nomi", flat=True).first() or ""
        raise ReviziyaXato(f"Taqsimot o'zgargan: {nomi} — kerak {soni:f}, mavjud {mavjud:f}.")
    if q.guruh in ("kam", "topilmadi") and q.holat == Holat.TOPILMADI:
        return  # allaqachon «topilmadi» holatida
    nishon_bolim = None
    if q.guruh == "boshqa_joyda":
        nishon_bolim = Bolim.objects.filter(pk=q.nishon_bolim_id).first()
        if nishon_bolim is None:
            raise ReviziyaXato("Nishon bo'lim topilmadi.")
    izoh = dict(sabab=REVIZIYA, hujjat_izoh=reviziya.nomi)
    qoldi = soni
    for t in mos:
        if qoldi <= 0:
            break
        m = min(t.soni, qoldi)
        qoldi -= m
        if q.guruh == "boshqa_joyda":
            yangi = kochir(t, m, nishon_bolim, kim, **izoh)
            if q.nishon_holat:
                holat_ozgartir(yangi, m, q.nishon_holat, kim, **izoh)
        elif q.guruh == "holat_boshqa":
            holat_ozgartir(t, m, q.nishon_holat, kim, **izoh)
        else:
            holat_ozgartir(t, m, Holat.TOPILMADI, kim, **izoh)


def reviziya_yop(reviziya: Reviziya, kim) -> None:
    """Yakunlangan reviziyani «qo'llangan» holatiga o'tkazadi."""
    with transaction.atomic():
        reviziya = _yakunlangan_qulfla(reviziya.pk)
        reviziya.holat = Reviziya.Holat.QOLLANGAN
        reviziya.qolladi = kim
        reviziya.qollangan_vaqt = timezone.now()
        reviziya.save(update_fields=["holat", "qolladi", "qollangan_vaqt"])
