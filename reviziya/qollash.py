"""Reviziya farqlarini taqsimotga yozish: yakunlashda avtomatik (`yakunla_va_yoz`), «Ochiq» ga qaytarishda teskari.

`qolla` reviziya qatorini butun chaqiruv davomida `select_for_update` bilan qulflaydi (parallel qo'llashlar navbatga
turadi); har kalit alohida savepoint'da — bitta kalit xatosi boshqalarini bekor qilmaydi, kalit esa hech qachon
qisman qo'llanmaydi. Har kalit natijasi `ReviziyaQollash` jurnaliga yoziladi.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from onec.models import AV
from vositalar.amallar import AmalXato, _ozgartir, holat_ozgartir, kochir
from vositalar.models import Bolim, Holat, Taqsimot, TaqsimotHarakat

from .models import Reviziya, ReviziyaQollash
from .servis import ReviziyaXato, yakunla
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


def qollashni_bekor_qil(reviziya: Reviziya, kalit: str, kim) -> None:
    """Qo'llangan vedomost qatorini teskari amal bilan qaytaradi; jurnal yozuvi «bekor» bo'ladi (yana qo'llash mumkin).

    Qo'llashdan keyin shu AV bilan boshqa amal (qo'lda ko'chirish, МОЛ akti, 1C sinxroni ...) bo'lgan bo'lsa — rad
    etiladi: teskari amal bu o'zgarishlarni buzishi mumkin, uni AV kartochkasida qo'lda tuzatish kerak.
    """
    with transaction.atomic():
        reviziya = Reviziya.objects.select_for_update().get(pk=reviziya.pk)
        if reviziya.holat != Reviziya.Holat.YAKUNLANGAN:
            raise ReviziyaXato("Reviziya yakunlanmagan.")
        jurnal = (
            reviziya.qollashlar.select_for_update().filter(kalit=kalit, natija=ReviziyaQollash.Natija.OK).first()
        )
        if jurnal is None:
            raise ReviziyaXato("Bu qator qo'llanmagan.")
        q = next((x for x in solishtir(reviziya) if x.kalit == kalit), None)
        if q is None:
            raise ReviziyaXato("Vedomost qatori topilmadi.")
        list(Taqsimot.objects.select_for_update().filter(filial_id=reviziya.filial_id, av_id=q.av_id).order_by("pk"))
        keyingi = (
            TaqsimotHarakat.objects.filter(av_id=q.av_id, filial_id=reviziya.filial_id, sana__gte=jurnal.qachon)
            .exclude(sabab=REVIZIYA, hujjat_izoh__startswith=reviziya.nomi)
            .order_by("sana")
            .first()
        )
        if keyingi is not None:
            raise ReviziyaXato(
                f"«{q.av_nomi}» ({q.inv}): yakunlashdan keyin bu AV bilan boshqa amal bajarilgan "
                f"({keyingi.get_sabab_display()}, {timezone.localtime(keyingi.sana):%d.%m.%Y %H:%M}) — "
                "uning o'zgarishini avtomatik qaytarib bo'lmaydi. AV kartochkasida qo'lda tuzating."
            )
        try:
            _teskari(reviziya, q, jurnal.soni, kim)
        except AmalXato as xato:
            raise ReviziyaXato(str(xato)) from None
        jurnal.natija = ReviziyaQollash.Natija.BEKOR
        jurnal.bekor_qildi = kim
        jurnal.bekor_vaqti = timezone.now()
        jurnal.save(update_fields=["natija", "bekor_qildi", "bekor_vaqti"])


def _teskari(reviziya, q, soni, kim) -> None:
    """`_taqsimotga` ning teskarisi: qo'llash natijasidagi (bo'lim, holat) qatorlardan `soni` donani vedomostdagi
    asl (bo'lim, holat) ga qaytaradi; qatorlar (har xil МОЛ) pk tartibida sarflanadi."""
    if q.guruh in ("kam", "topilmadi") and q.holat == Holat.TOPILMADI:
        return  # qo'llashda ham hech narsa o'zgarmagan
    if q.guruh == "boshqa_joyda":
        manba = (q.nishon_bolim_id, q.nishon_holat or q.holat)
    elif q.guruh == "holat_boshqa":
        manba = (q.bolim_id, q.nishon_holat)
    else:
        manba = (q.bolim_id, Holat.TOPILMADI)
    qatorlar = Taqsimot.objects.filter(av_id=q.av_id, filial_id=reviziya.filial_id).order_by("pk")
    mos = [t for t in qatorlar if (t.bolim_id, t.holat) == manba]
    mavjud = sum((t.soni for t in mos), NOL)
    if mavjud < soni:
        nomi = AV.objects.filter(pk=q.av_id).values_list("nomi", flat=True).first() or ""
        raise ReviziyaXato(f"Taqsimot o'zgargan: {nomi} — qaytarish uchun {soni:f} kerak, mavjud {mavjud:f}.")
    izoh = f"{reviziya.nomi} — qo'llash bekor qilindi"
    qoldi = soni
    for t in mos:
        if qoldi <= 0:
            break
        m = min(t.soni, qoldi)
        qoldi -= m
        _ozgartir(t, m, kim, REVIZIYA, bolim=q.bolim_id, holat=q.holat, hujjat_izoh=izoh)


def yakunla_va_yoz(reviziya: Reviziya, kim) -> list[ReviziyaQollash]:
    """Ochiq reviziyani yakunlaydi va barcha farqlarni (kam/topilmadi, boshqa joyda, holati boshqa) taqsimotga yozadi.

    Sanash yopilishi va yozish — bitta tranzaksiyada. Har farq alohida savepoint'da (`qolla`): bittasini yozib
    bo'lmasa (masalan, taqsimot oraliqda o'zgargan), u jurnalda «xato» sababi bilan qoladi, qolganlari yoziladi.
    «Bo'limsiz» ga ko'chish yozilmaydi (xona noma'lum) — `qollanadimi`.
    """
    with transaction.atomic():
        yakunla(reviziya, kim)
        kalitlar = [q.kalit for q in solishtir(reviziya) if qollanadimi(q)]
        return qolla(reviziya, kalitlar, kim) if kalitlar else []


def ochiqqa_qaytar(reviziya: Reviziya, kim) -> None:
    """Yakunlangan reviziyani «Ochiq» ga qaytaradi: taqsimotga yozilgan har farq teskari amal bilan qaytariladi.

    Hammasi yoki hech biri: bittasini qaytarib bo'lmasa (yakunlashdan keyin shu AV bilan boshqa amal bo'lgan) — rad
    etiladi va reviziya «Yakunlangan» qoladi. Yozilmagan farqlarning xato yozuvlari o'chiriladi (qayta yakunlashda
    yangidan yoziladi).
    """
    with transaction.atomic():
        reviziya = _yakunlangan_qulfla(reviziya.pk)
        for jurnal in reviziya.qollashlar.filter(natija=ReviziyaQollash.Natija.OK).order_by("-pk"):
            qollashni_bekor_qil(reviziya, jurnal.kalit, kim)
        reviziya.qollashlar.filter(natija=ReviziyaQollash.Natija.XATO).delete()
        reviziya.holat = Reviziya.Holat.OCHIQ
        reviziya.yakunladi = None
        reviziya.yakunlangan_vaqt = None
        reviziya.save(update_fields=["holat", "yakunladi", "yakunlangan_vaqt"])
