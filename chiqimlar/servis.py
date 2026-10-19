"""1C chiqim harakatlaridan `ChiqimHujjat` yozuvlarini yaratish/yangilash/bekor qilish va tur taxmini."""
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from jurnal import yoz as jurnal_yoz
from onec.models import Harakat1C
from vositalar.models import Sozlama

from .models import ChiqimHujjat

# Chiqimdan oldin yoki keyin (±) shu muddat ichida boshqa filialda kirim bo'lsa — o'tkazish deb taxmin qilinadi.
TAXMIN_OYNASI = timedelta(days=3)
SPISANIE = "СписаниеОС"


def taxmin_qil(av_id: int, filial_id: int, sana: datetime, hujjat_turi: str) -> tuple[str, int | None]:
    """(tur, qabul_filial_id): spisanie -> hisobdan chiqarildi; ±oynada boshqa filialga kirim -> o'tkazish; aks holda sotildi."""
    if SPISANIE in (hujjat_turi or ""):
        return ChiqimHujjat.Tur.HISOBDAN_CHIQARILDI, None
    kirim = (
        Harakat1C.objects.filter(
            av_id=av_id, vid=Harakat1C.Vid.KIRIM, filial__isnull=False, soni__gt=0,
            sana__gte=sana - TAXMIN_OYNASI, sana__lte=sana + TAXMIN_OYNASI,
        )
        .exclude(filial_id=filial_id)
        .order_by("sana", "id")
        .first()
    )
    if kirim is not None:
        return ChiqimHujjat.Tur.OTKAZISH, kirim.filial_id
    return ChiqimHujjat.Tur.SOTILDI, None


def chiqimlarni_yangila(dan: datetime, gacha: datetime) -> dict:
    """[dan, gacha] (aware) oralig'idagi 1C chiqimlarini `ChiqimHujjat`ga aks ettiradi."""
    stat = {"yaratildi": 0, "yangilandi": 0, "bekor": 0, "qaytdi": 0}
    boshlanish = Sozlama.ol().chiqim_boshlanishi
    if boshlanish is None:
        return stat
    quyi = max(dan, boshlanish)

    guruhlar = {}
    qatorlar = Harakat1C.objects.filter(
        vid=Harakat1C.Vid.CHIQIM, soni__gt=0, sana__gte=quyi, sana__lte=gacha, filial__isnull=False
    ).order_by("sana", "id")
    for h in qatorlar:
        kalit = (h.hujjat_ref, h.av_id, h.filial_id)
        g = guruhlar.get(kalit)
        if g is None:
            guruhlar[kalit] = {
                "sana": h.sana, "hujjat_turi": h.hujjat_turi, "hujjat_raqami": h.hujjat_raqami,
                "soni": Decimal(h.soni), "summa": Decimal(h.summa),
            }
        else:
            g["soni"] += h.soni
            g["summa"] += h.summa

    with transaction.atomic():
        mavjud = {
            (c.hujjat_ref, c.av_id, c.filial_id): c
            for c in ChiqimHujjat.objects.select_for_update().filter(sana__gte=quyi, sana__lte=gacha)
        }
        # Oraliqdan tashqarida turgan, lekin guruhda uchrayotgan yozuvlar ham kerak bo'ladi.
        for (ref, av_id, filial_id), g in guruhlar.items():
            c = mavjud.get((ref, av_id, filial_id))
            if c is None:
                c = ChiqimHujjat.objects.filter(hujjat_ref=ref, av_id=av_id, filial_id=filial_id).first()
            if c is None:
                tur, qabul = taxmin_qil(av_id, filial_id, g["sana"], g["hujjat_turi"])
                ChiqimHujjat.objects.create(
                    hujjat_turi=g["hujjat_turi"], hujjat_raqami=g["hujjat_raqami"], hujjat_ref=ref,
                    sana=g["sana"], av_id=av_id, filial_id=filial_id, soni=g["soni"], summa=g["summa"],
                    taxmin_tur=tur,
                )
                stat["yaratildi"] += 1
            elif c.holat == ChiqimHujjat.Holat.KUTILMOQDA and (
                (c.soni, c.summa, c.sana) != (g["soni"], g["summa"], g["sana"])
            ):
                c.soni, c.summa, c.sana = g["soni"], g["summa"], g["sana"]
                c.save(update_fields=["soni", "summa", "sana"])
                stat["yangilandi"] += 1
            elif c.holat == ChiqimHujjat.Holat.BEKOR:
                # 1C hujjati qayta o'tkazildi: yana tasdiq kutadi (aks holda K=0 va taqsimot tasdiqsiz o'chadi).
                c.holat = ChiqimHujjat.Holat.KUTILMOQDA
                c.soni, c.summa, c.sana = g["soni"], g["summa"], g["sana"]
                c.save(update_fields=["holat", "soni", "summa", "sana"])
                jurnal_yoz.yoz(None, c, "holat", ChiqimHujjat.Holat.BEKOR, ChiqimHujjat.Holat.KUTILMOQDA)
                stat["qaytdi"] += 1

        for kalit, c in mavjud.items():
            if kalit not in guruhlar and c.holat == ChiqimHujjat.Holat.KUTILMOQDA:
                c.holat = ChiqimHujjat.Holat.BEKOR
                c.save(update_fields=["holat"])
                jurnal_yoz.yoz(None, c, "holat", ChiqimHujjat.Holat.KUTILMOQDA, ChiqimHujjat.Holat.BEKOR)
                stat["bekor"] += 1
    return stat


def kutilayotgan(filtr: Q | None = None) -> dict[tuple[int, int], Decimal]:
    """K (spec §6.5): {(av_id, filial_id): Σ soni} — `kutilmoqda` chiqimlar; `filtr` — qo'shimcha shart."""
    qs = ChiqimHujjat.objects.filter(holat=ChiqimHujjat.Holat.KUTILMOQDA)
    if filtr is not None:
        qs = qs.filter(filtr)
    qatorlar = qs.order_by().values_list("av_id", "filial_id").annotate(jami=Sum("soni"))
    return {(av, filial): jami for av, filial, jami in qatorlar}
