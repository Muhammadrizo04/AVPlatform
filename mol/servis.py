"""МОЛ aktlari: qoralama yaratish va tasdiqlash (spec §7.6, §8).

Tasdiqlash — bitta tranzaksiya: avval akt qatorlaridagi barcha (AV, filial) taqsimot qatorlari bitta so'rovda
pk tartibida qulflanadi (`moslashtir` bilan bir xil tartib — deadlock yo'q), keyin hammasi tekshiriladi, keyin
`mol_ozgartir` chaqiriladi. Istalgan xato -> `AktXato`, hech narsa o'zgarmaydi.
"""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import connection, transaction
from django.db.models import Max, Q
from django.utils import timezone

from onec.models import AV, Xodim
from vositalar.amallar import AmalXato, mol_ozgartir
from vositalar.amortizatsiya import dona_narxi
from vositalar.models import Taqsimot

from .models import MolAkt, MolAktQator

NOL = Decimal("0")
TIYIN = Decimal("0.01")
AKT_RAQAM_QULFI = 7310002  # akt raqamini berish uchun PostgreSQL advisory lock kaliti (sinxron — 7310001)


class AktXato(Exception):
    """Aktni yaratib/tasdiqlab bo'lmaydi; matni foydalanuvchiga ko'rsatiladi."""


def akt_yarat(topshiruvchi, qabul_qiluvchi, qatorlar, kim, izoh: str = "") -> MolAkt:
    """Qoralama akt. `qatorlar` — [(Taqsimot, soni)]; har qatorning `mol` i topshiruvchiga teng bo'lishi shart.
    Taqsimot bu yerda o'zgarmaydi."""
    if not qatorlar:
        raise AktXato("Aktga kamida bitta qator qo'shing.")
    if topshiruvchi is not None and topshiruvchi.pk == qabul_qiluvchi.pk:
        raise AktXato("Topshiruvchi va qabul qiluvchi bir xil bo'lmasligi kerak.")
    topshiruvchi_id = None if topshiruvchi is None else topshiruvchi.pk
    tekshirilgan = []
    for taqsimot, soni in qatorlar:
        try:
            soni = soni if isinstance(soni, Decimal) else Decimal(str(soni))
        except ArithmeticError:
            raise AktXato("Sonni to'g'ri kiriting.") from None
        if not soni.is_finite() or soni <= 0:
            raise AktXato("Qator soni noldan katta bo'lishi kerak.")
        if taqsimot.mol_id != topshiruvchi_id:
            raise AktXato("Qator topshiruvchining МОЛ'iga tegishli emas.")
        if soni > taqsimot.soni:
            raise AktXato(f"Soni qatordagi miqdordan ({taqsimot.soni:f}) oshib ketdi.")
        tekshirilgan.append((taqsimot, soni))

    with transaction.atomic():
        akt = MolAkt.objects.create(
            raqam=_keyingi_raqam(), topshiruvchi=topshiruvchi, qabul_qiluvchi=qabul_qiluvchi, izoh=izoh, tuzdi=kim
        )
        MolAktQator.objects.bulk_create(
            MolAktQator(
                akt=akt, av_id=t.av_id, filial_id=t.filial_id, bolim_id=t.bolim_id, holat=t.holat, soni=soni
            )
            for t, soni in tekshirilgan
        )
    return akt


def _keyingi_raqam() -> int:
    """max(raqam)+1. Avval tranzaksiya darajasidagi advisory lock (`AKT_RAQAM_QULFI`) olinadi: parallel yaratuvchilar
    tranzaksiya tugaguncha ketma-ket ishlaydi (bo'sh jadvalda ham), shuning uchun bir xil raqam berilmaydi.
    Tranzaksiya ichida chaqirilishi shart."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [AKT_RAQAM_QULFI])
    oxirgi = MolAkt.objects.aggregate(m=Max("raqam"))["m"]
    return 1 if oxirgi is None else oxirgi + 1


def akt_tasdiqla(akt: MolAkt, kim) -> None:
    """Aktni tasdiqlaydi: har qator topshiruvchidan qabul qiluvchiga o'tadi. Bitta xato -> `AktXato`, o'zgarishsiz."""
    try:
        with transaction.atomic():
            _tasdiqla(akt, kim)
    except AmalXato as xato:
        raise AktXato(str(xato)) from xato


def kalit(obyekt) -> tuple:
    """Akt qatori va taqsimot qatorini solishtirish kaliti."""
    return obyekt.av_id, obyekt.filial_id, obyekt.bolim_id, obyekt.holat


def _tasdiqla(akt: MolAkt, kim) -> None:
    joriy = MolAkt.objects.select_for_update().get(pk=akt.pk)
    if joriy.holat != MolAkt.Holat.QORALAMA:
        raise AktXato("Akt allaqachon tasdiqlangan.")
    qatorlar = list(joriy.qatorlar.order_by("pk"))
    if not qatorlar:
        raise AktXato("Aktda qator yo'q.")

    # 1) Barcha (AV, filial) qatorlari bitta so'rovda, pk tartibida qulflanadi.
    juftlar = {(q.av_id, q.filial_id) for q in qatorlar}
    shart = Q()
    for av_id, filial_id in juftlar:
        shart |= Q(av_id=av_id, filial_id=filial_id)
    qulflangan = list(Taqsimot.objects.select_for_update().filter(shart).order_by("pk"))

    # 2) Tekshiruvlar.
    qabul = Xodim.objects.get(pk=joriy.qabul_qiluvchi_id)
    if qabul.ishdan_bushagan or qabul.neaktiv or qabul.onec_da_yoq:
        raise AktXato(f"Qabul qiluvchi ({qabul.ism}) faol xodim emas: ishdan bo'shagan yoki o'chirilgan.")
    arxiv = set(
        AV.objects.arxiv().filter(pk__in={q.av_id for q in qatorlar}).values_list("nomi", flat=True)
    )
    if arxiv:
        raise AktXato(f"Arxivdagi AV bilan amal bajarib bo'lmaydi: {', '.join(sorted(arxiv))}.")

    # Bir taqsimot qatoriga ishora qiluvchi takror qatorlar avval qo'shiladi.
    kerak = defaultdict(lambda: NOL)
    for q in qatorlar:
        kerak[kalit(q)] += q.soni
    mavjud = {kalit(t): t for t in qulflangan if t.mol_id == joriy.topshiruvchi_id}
    for k, soni in kerak.items():
        t = mavjud.get(k)
        if t is None:
            raise AktXato("Tasdiqlashdan oldin taqsimot o'zgargan: qator topilmadi. Aktni qayta tuzing.")
        if soni > t.soni:
            raise AktXato(
                f"Topshiruvchida yetarli miqdor yo'q: kerak {soni:f}, mavjud {t.soni:f} ({t.av.nomi})."
            )

    # 3) Amal: har taqsimot qatori uchun bir marta, yig'indi son bilan.
    for k, soni in kerak.items():
        mol_ozgartir(mavjud[k], soni, qabul, kim, hujjat_izoh=joriy.nomi)

    # 4) Tasdiqlangan akt o'zgarmaydi (spec §7.6): qiymat uchun bir dona narxi shu paytdagi 1C ma'lumotidan saqlanadi.
    narxlar = {
        av.pk: dona_narxi(av.jami_summa, av.jami_soni).quantize(TIYIN, ROUND_HALF_UP)
        for av in AV.objects.qoldiq_bilan().filter(pk__in={q.av_id for q in qatorlar})
    }
    for q in qatorlar:
        q.dona_narxi = narxlar.get(q.av_id, NOL)
    MolAktQator.objects.bulk_update(qatorlar, ["dona_narxi"])

    joriy.holat = MolAkt.Holat.TASDIQLANGAN
    joriy.tasdiqladi = kim
    joriy.tasdiq_vaqti = timezone.now()
    joriy.save(update_fields=["holat", "tasdiqladi", "tasdiq_vaqti"])
    akt.holat, akt.tasdiqladi, akt.tasdiq_vaqti = joriy.holat, joriy.tasdiqladi, joriy.tasdiq_vaqti
