"""Taqsimotni 1C qoldig'i bilan moslash (spec §6.3).

Har sinxrondan keyin, sinxron tranzaksiyasi ichida chaqiriladi. 1C — qoldiq manbai; bu yerda har (AV, filial)
uchun `d = 1C qoldig'i - sum(taqsimot)` hisoblanib, farq «taqsimlanmagan» qatorga (bolim/MOL bo'sh,
`ishlatilmoqda`) yoziladi yoki undan ayiriladi. Har o'zgarish `TaqsimotHarakat` va Jurnal («1C sinxron») ga yoziladi.
Qayta chaqirish hech narsani o'zgartirmaydi.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Min, Sum
from django.utils import timezone

from jurnal.yoz import yoz
from onec.models import AV, AVQoldiq, Harakat1C

from .models import AVKartochka, Holat, Taqsimot, TaqsimotHarakat

NOL = Decimal("0")
Sabab = TaqsimotHarakat.Sabab


class MoslashXato(Exception):
    """Moslashdan keyin Σ taqsimot 1C qoldig'iga teng emas (mos emas holatdan tashqari)."""


def farq(av: AV, filial) -> Decimal:
    """1C qoldig'i - sum(taqsimot) shu (AV, filial) uchun. Manfiy — taqsimot 1C'dan ortiq (mos emas)."""
    qoldiq = AVQoldiq.objects.filter(av=av, filial=filial).aggregate(s=Sum("soni"))["s"] or NOL
    taqsimot = Taqsimot.objects.filter(av=av, filial=filial).aggregate(s=Sum("soni"))["s"] or NOL
    return qoldiq - taqsimot


def moslashtir() -> dict:
    """Taqsimotni 1C qoldig'iga moslaydi. Statistika (sonlar — (AV, filial) juftlari):
    `yangi_kartochka`, `kopaydi`, `kamaydi`, `nolga_tushdi`, `mos_emas` (moslashdan keyin farq < 0)."""
    with transaction.atomic():
        statistika = {"yangi_kartochka": 0, "kopaydi": 0, "kamaydi": 0, "nolga_tushdi": 0, "mos_emas": 0}
        statistika["yangi_kartochka"] = _kartochkalar()

        # Bir (av, filial) uchun bir nechta tashkilot qatori bo'lishi mumkin — yig'iladi.
        qoldiq = _yigindi(AVQoldiq.objects)
        # Qatorlar qulflanadi (spec §8): foydalanuvchining parallel ko'chirishi o'qish va yozish orasida kirmaydi.
        # PostgreSQL FOR UPDATE'ni GROUP BY bilan qabul qilmaydi — yig'indi Python'da, qulflangan qatorlardan.
        taqsimot, taqsimlanmagan = {}, {}
        for t in Taqsimot.objects.select_for_update().order_by("pk"):
            juft = (t.av_id, t.filial_id)
            taqsimot[juft] = taqsimot.get(juft, NOL) + t.soni
            if t.bolim_id is None and t.mol_id is None and t.holat == Holat.ISHLATILMOQDA:
                taqsimlanmagan[juft] = t

        ishlar = []  # (juft, tur, miqdor)
        for juft in qoldiq.keys() | taqsimot.keys():
            q = max(qoldiq.get(juft, NOL), NOL)
            t = taqsimot.get(juft, NOL)
            if q <= 0:
                if t > 0:
                    ishlar.append((juft, "nolga", t))
                continue
            d = q - t
            if d > 0:
                ishlar.append((juft, "kopaydi", d))
            elif d < 0:
                olinadi = min(taqsimlanmagan[juft].soni if juft in taqsimlanmagan else NOL, -d)
                if olinadi > 0:
                    ishlar.append((juft, "kamaydi", olinadi))

        izohlar = _hujjat_izohlari({juft for juft, _, _ in ishlar})
        for juft, tur, miqdor in ishlar:
            izoh = izohlar.get(juft, "")
            if tur == "nolga":
                _nolga_tushdi(juft, izoh)
                statistika["nolga_tushdi"] += 1
            elif tur == "kopaydi":
                _kopaydi(juft, miqdor, taqsimlanmagan.get(juft), izoh)
                statistika["kopaydi"] += 1
            else:
                _kamaydi(taqsimlanmagan[juft], miqdor, izoh)
                statistika["kamaydi"] += 1

        _ishga_tushgan_sanalar()
        statistika["mos_emas"] = _invariantni_tekshir()
        return statistika


def _invariantni_tekshir() -> int:
    """Bazadagi haqiqiy yig'indilar bo'yicha invariantni tekshiradi (spec §8). Faqat Σ taqsimot > 1C qoldig'i
    bo'lgan (mos emas, farq < 0) juftlar ruxsat etiladi; ularning soni qaytariladi. Boshqasi — `MoslashXato`
    (sinxron tranzaksiyasi rollback bo'ladi)."""
    qoldiq = _yigindi(AVQoldiq.objects)
    taqsimot = _yigindi(Taqsimot.objects)
    mos_emas = 0
    for juft in qoldiq.keys() | taqsimot.keys():
        q = max(qoldiq.get(juft, NOL), NOL)
        t = taqsimot.get(juft, NOL)
        if t < q or (q <= 0 and t != 0):
            raise MoslashXato(f"Taqsimot invarianti buzildi: av={juft[0]} filial={juft[1]} 1C={q} taqsimot={t}")
        if t > q:
            mos_emas += 1
    return mos_emas


def _yigindi(manba) -> dict:
    """{(av_id, filial_id): Σ soni} — bitta aggregat so'rov."""
    qatorlar = manba.order_by().values("av_id", "filial_id").annotate(jami=Sum("soni"))
    return {(q["av_id"], q["filial_id"]): q["jami"] for q in qatorlar}


def _kartochkalar() -> int:
    """Kartochkasi yo'q har AV uchun (qoldig'i 0 bo'lsa ham) AVKartochka yaratadi."""
    yangilar = [AVKartochka(av_id=pk) for pk in AV.objects.filter(kartochka__isnull=True).values_list("pk", flat=True)]
    AVKartochka.objects.bulk_create(yangilar, batch_size=500)
    return len(yangilar)


def _hujjat_izohlari(juftlar: set) -> dict:
    """{(av_id, filial_id): "<hujjat_turi> <hujjat_raqami>"} — shu juftda sonni o'zgartirgan oxirgi 1C harakati.

    Soni 0 bo'lgan harakatlar (ПереоценкаОС, РасходыНаОС) taqsimotga sabab bo'lmaydi va hisobga olinmaydi.
    """
    if not juftlar:
        return {}
    harakatlar = (
        Harakat1C.objects.filter(
            av_id__in={av for av, _ in juftlar}, filial_id__in={filial for _, filial in juftlar}
        )
        .exclude(soni=0)
        .order_by("av_id", "filial_id", "-sana", "-id")
        .distinct("av_id", "filial_id")
    )
    return {
        (h.av_id, h.filial_id): f"{h.hujjat_turi} {h.hujjat_raqami}".strip()[:255]
        for h in harakatlar
        if (h.av_id, h.filial_id) in juftlar
    }


def _yoz(juft, sabab, izoh, soni, *, eski=None, yangi=None) -> None:
    """TaqsimotHarakat; eski/yangi — (bolim_id, mol_id, holat) yoki None (bo'sh)."""
    eski_bolim, eski_mol, eski_holat = eski or (None, None, "")
    yangi_bolim, yangi_mol, yangi_holat = yangi or (None, None, "")
    TaqsimotHarakat.objects.create(
        av_id=juft[0], filial_id=juft[1],
        eski_bolim_id=eski_bolim, eski_mol_id=eski_mol, eski_holat=eski_holat,
        yangi_bolim_id=yangi_bolim, yangi_mol_id=yangi_mol, yangi_holat=yangi_holat,
        soni=soni, kim=None, sabab=sabab, hujjat_izoh=izoh,
    )


def _kopaydi(juft, miqdor, qator, izoh) -> None:
    """`miqdor` dona taqsimlanmagan qatorga qo'shiladi (qator yo'q bo'lsa yaratiladi)."""
    if qator is None:
        qator = Taqsimot.objects.create(
            av_id=juft[0], filial_id=juft[1], holat=Holat.ISHLATILMOQDA, soni=miqdor
        )
        eski = NOL
    else:
        eski = qator.soni
        qator.soni = eski + miqdor
        qator.save(update_fields=["soni"])
    _yoz(juft, Sabab.ONEC_KOPAYDI, izoh, miqdor, yangi=(None, None, Holat.ISHLATILMOQDA))
    yoz(None, qator, "soni", eski, qator.soni)


def _kamaydi(qator, miqdor, izoh) -> None:
    """Taqsimlanmagan qatordan `miqdor` dona ayiriladi (0 bo'lsa qator o'chiriladi)."""
    juft = (qator.av_id, qator.filial_id)
    eski = qator.soni
    yangi = eski - miqdor
    _yoz(juft, Sabab.ONEC_KAMAYDI, izoh, miqdor, eski=(None, None, Holat.ISHLATILMOQDA))
    if yangi > 0:
        qator.soni = yangi
        qator.save(update_fields=["soni"])
    else:
        Taqsimot.objects.filter(pk=qator.pk).delete()
    yoz(None, qator, "soni", eski, max(yangi, NOL))


def _nolga_tushdi(juft, izoh) -> None:
    """Filialdagi barcha qatorlar o'chiriladi; har qator uchun alohida harakat."""
    qatorlar = list(Taqsimot.objects.filter(av_id=juft[0], filial_id=juft[1]))
    Taqsimot.objects.filter(pk__in=[q.pk for q in qatorlar]).delete()
    for q in qatorlar:
        _yoz(juft, Sabab.ONEC_NOLGA_TUSHDI, izoh, q.soni, eski=(q.bolim_id, q.mol_id, q.holat))
        yoz(None, q, "soni", q.soni, NOL)


def _ishga_tushgan_sanalar() -> None:
    """Bo'sh `ishga_tushgan_sana` — AV'ning eng erta `kirim` harakati sanasi (mahalliy sana). Qo'lda kiritilgani
    o'zgarmaydi."""
    bosh = {k.av_id: k for k in AVKartochka.objects.filter(ishga_tushgan_sana__isnull=True)}
    if not bosh:
        return
    eng_erta = (
        Harakat1C.objects.filter(av_id__in=list(bosh), vid=Harakat1C.Vid.KIRIM)
        .order_by()
        .values("av_id")
        .annotate(sana=Min("sana"))
    )
    ozgargan = []
    for q in eng_erta:
        kartochka = bosh[q["av_id"]]
        kartochka.ishga_tushgan_sana = timezone.localdate(q["sana"])
        ozgargan.append(kartochka)
    AVKartochka.objects.bulk_update(ozgargan, ["ishga_tushgan_sana"], batch_size=500)
    for kartochka in ozgargan:
        yoz(None, kartochka, "ishga_tushgan_sana", None, kartochka.ishga_tushgan_sana)
