"""МОЛ aktlari: qoralama yaratish va tasdiqlash (spec §7.6, §8).

Tasdiqlash — bitta tranzaksiya: avval akt qatorlaridagi barcha (AV, filial) taqsimot qatorlari bitta so'rovda
pk tartibida qulflanadi (`moslashtir` bilan bir xil tartib — deadlock yo'q), keyin hammasi tekshiriladi, keyin
`mol_ozgartir` chaqiriladi. Istalgan xato -> `AktXato`, hech narsa o'zgarmaydi.
"""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from onec.models import AV, Xodim
from vositalar.amallar import AmalXato, mol_ozgartir
from vositalar.models import Taqsimot

from .models import MolAkt, MolAktQator

NOL = Decimal("0")


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
    """max(raqam)+1; oxirgi qator qulflanadi, shuning uchun parallel yaratuvchilar ketma-ket ishlaydi."""
    oxirgi = MolAkt.objects.select_for_update().order_by("-raqam").first()
    return 1 if oxirgi is None else oxirgi.raqam + 1


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

    joriy.holat = MolAkt.Holat.TASDIQLANGAN
    joriy.tasdiqladi = kim
    joriy.tasdiq_vaqti = timezone.now()
    joriy.save(update_fields=["holat", "tasdiqladi", "tasdiq_vaqti"])
    akt.holat, akt.tasdiqladi, akt.tasdiq_vaqti = joriy.holat, joriy.tasdiqladi, joriy.tasdiq_vaqti
