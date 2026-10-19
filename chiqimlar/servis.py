"""1C chiqim harakatlaridan `ChiqimHujjat` yozuvlarini yaratish/yangilash/bekor qilish, tur taxmini va tasdiqlash."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from jurnal import yoz as jurnal_yoz
from onec.models import AVQoldiq, Harakat1C
from vositalar.amallar import AmalXato, ayir_va_yoz, holat_ozgartir, kochir
from vositalar.models import Holat, Sozlama, Taqsimot, TaqsimotHarakat

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


class ChiqimXato(Exception):
    """Chiqimni tasdiqlab bo'lmaydi; matni foydalanuvchiga ko'rsatiladi (o'zbekcha)."""


NOL = Decimal("0")
_SABAB = {
    ChiqimHujjat.Tur.SOTILDI: TaqsimotHarakat.Sabab.SOTILDI,
    ChiqimHujjat.Tur.OTKAZISH: TaqsimotHarakat.Sabab.OTKAZILDI,
    ChiqimHujjat.Tur.HISOBDAN_CHIQARILDI: TaqsimotHarakat.Sabab.HISOBDAN_CHIQARILDI,
}


def taqsimot_qatorlari(chiqim: ChiqimHujjat) -> list[Taqsimot]:
    """A filialdagi shu AV'ning taqsimot qatorlari (tasdiqlash formasi uchun), pk tartibida."""
    return list(
        Taqsimot.objects.filter(av_id=chiqim.av_id, filial_id=chiqim.filial_id)
        .select_related("bolim", "mol")
        .order_by("pk")
    )


def tasdiqla(
    chiqim: ChiqimHujjat, tur: str, qatorlar: dict[int, Decimal], kim, *, kutilgan_soni: Decimal,
    qabul_filial=None, b_bolim=None, b_holat: str = "", izoh: str = "",
) -> None:
    """Kutilayotgan 1C chiqimini tasdiqlaydi (spec §6.5): A filialdagi tanlangan qatorlardan jami `chiqim.soni` dona
    olib tashlanadi; `otkazish`da B'ga kelgan taqsimlanmagan donalar ixtiyoriy ravishda `b_bolim`ga joylanadi.

    `qatorlar` — {taqsimot_pk: soni} (0 lar e'tiborsiz); `kutilgan_soni` — forma ko'rsatgan chiqim soni.
    Qulf tartibi `moslashtir` bilan bir xil (ChiqimHujjat -> Taqsimot pk tartibida) — deadlock bo'lmaydi.
    Arxiv AV ham tasdiqlanadi (A juft uchun arxiv tekshiruvi yo'q). Xatoda `ChiqimXato`, tranzaksiya qaytariladi."""
    with transaction.atomic():
        c = ChiqimHujjat.objects.select_for_update().filter(pk=chiqim.pk).first()
        if c is None:
            raise ChiqimXato("Chiqim topilmadi. Sahifani yangilang.")
        if c.holat != ChiqimHujjat.Holat.KUTILMOQDA:
            raise ChiqimXato("Bu chiqim allaqachon tasdiqlangan.")
        if c.soni != kutilgan_soni:
            raise ChiqimXato("1C'da chiqim soni o'zgargan, sahifani yangilang.")
        if tur not in ChiqimHujjat.Tur.values:
            raise ChiqimXato("Chiqim turini tanlang.")
        otkazish = tur == ChiqimHujjat.Tur.OTKAZISH
        if otkazish:
            if qabul_filial is None:
                raise ChiqimXato("Qabul qiluvchi filialni tanlang.")
            if qabul_filial.pk == c.filial_id:
                raise ChiqimXato("Qabul qiluvchi filial chiqim filialidan boshqa bo'lishi kerak.")
        else:
            qabul_filial, b_bolim, b_holat = None, None, ""
        if b_bolim is not None:
            if b_bolim.filial_id != qabul_filial.pk:
                raise ChiqimXato("Bo'lim qabul qiluvchi filialga tegishli bo'lishi kerak.")
            if b_holat and b_holat not in Holat.values:
                raise ChiqimXato("Noma'lum holat.")

        # A va B juftlarining barcha qatorlari bitta so'rovda, pk tartibida qulflanadi.
        shart = Q(av_id=c.av_id, filial_id=c.filial_id)
        if otkazish:
            shart |= Q(av_id=c.av_id, filial_id=qabul_filial.pk)
        qulflangan = list(Taqsimot.objects.select_for_update().filter(shart).order_by("pk"))
        a_qatorlar = {t.pk: t for t in qulflangan if t.filial_id == c.filial_id}

        tanlangan = _tekshir_qatorlar(qatorlar, a_qatorlar, c.soni)

        hujjat_izoh = f"{c.hujjat_turi} {c.hujjat_raqami}".strip()
        for qator, soni in tanlangan:
            ayir_va_yoz(qator, soni, kim, _SABAB[tur], hujjat_izoh)

        eski = (c.holat, c.tur, c.qabul_filial_id, c.izoh)
        c.holat = ChiqimHujjat.Holat.TASDIQLANGAN
        c.tur = tur
        c.qabul_filial = qabul_filial
        c.izoh = izoh
        c.kim = kim
        c.qachon = timezone.now()
        c.save(update_fields=["holat", "tur", "qabul_filial", "izoh", "kim", "qachon"])
        for maydon, oldingi, yangi in zip(
            ("holat", "tur", "qabul_filial", "izoh"), eski, (c.holat, c.tur, c.qabul_filial_id, c.izoh)
        ):
            if oldingi != yangi:
                jurnal_yoz.yoz(kim, c, maydon, oldingi, yangi)

        if b_bolim is not None:
            _b_ga_joyla(c, qulflangan, qabul_filial, b_bolim, b_holat, kim)

        _tekshir_invariant(c)
    chiqim.refresh_from_db()


def _tekshir_qatorlar(qatorlar: dict, a_qatorlar: dict, jami: Decimal) -> list:
    """[(qulflangan qator, soni)]; har kalit A juft qatori, 0 < soni <= qator.soni, Σ = jami."""
    tanlangan = []
    for pk, soni in qatorlar.items():
        try:
            soni = soni if isinstance(soni, Decimal) else Decimal(str(soni))
            togri = soni.is_finite()
        except (InvalidOperation, ValueError):
            togri = False
        if not togri:
            raise ChiqimXato("Sonni to'g'ri kiriting.")
        if soni == 0:
            continue
        qator = a_qatorlar.get(pk)
        if qator is None:
            raise ChiqimXato("Taqsimot qatori topilmadi: u o'zgargan bo'lishi mumkin. Sahifani yangilang.")
        if soni < 0:
            raise ChiqimXato("Soni noldan katta bo'lishi kerak.")
        if soni.as_tuple().exponent < -3:
            raise ChiqimXato("Sonda ko'pi bilan 3 ta kasr xonasi bo'lishi mumkin.")
        if soni > qator.soni:
            raise ChiqimXato(f"Soni qatordagi miqdordan ({qator.soni:f}) oshib ketdi.")
        tanlangan.append((qator, soni))
    yigindi = sum((s for _, s in tanlangan), NOL)
    if yigindi != jami:
        raise ChiqimXato(
            f"Tanlangan sonlar yig'indisi ({yigindi:f}) chiqim soniga ({jami:f}) teng bo'lishi kerak."
        )
    return tanlangan


def _b_ga_joyla(c: ChiqimHujjat, qulflangan: list, qabul_filial, b_bolim, b_holat: str, kim) -> None:
    """B'dagi taqsimlanmagan qatordan min(chiqim soni, qator soni) donani `b_bolim`ga ko'chiradi; `b_holat` berilsa —
    aynan shu donalarning holati o'zgaradi. Taqsimlanmagan qator bo'lmasa — hech narsa qilinmaydi (Review Focus 5)."""
    qator = next(
        (
            t for t in qulflangan
            if t.filial_id == qabul_filial.pk and t.bolim_id is None and t.mol_id is None
            and t.holat == Holat.ISHLATILMOQDA
        ),
        None,
    )
    if qator is None:
        return
    soni = min(c.soni, qator.soni)
    try:
        nishon = kochir(qator, soni, b_bolim, kim)
        if b_holat and b_holat != nishon.holat:
            holat_ozgartir(nishon, soni, b_holat, kim)
    except AmalXato as xato:
        raise ChiqimXato(str(xato)) from None


def _tekshir_invariant(c: ChiqimHujjat) -> None:
    """A juft: Σ taqsimot >= max(1C, 0) + K (qolgan kutilayotganlar); kam bo'lsa — `ChiqimXato`."""
    qoldiq = AVQoldiq.objects.filter(av_id=c.av_id, filial_id=c.filial_id).aggregate(s=Sum("soni"))["s"] or NOL
    taqsimot = Taqsimot.objects.filter(av_id=c.av_id, filial_id=c.filial_id).aggregate(s=Sum("soni"))["s"] or NOL
    k = kutilayotgan(Q(av_id=c.av_id, filial_id=c.filial_id)).get((c.av_id, c.filial_id), NOL)
    if taqsimot < max(qoldiq, NOL) + k:
        raise ChiqimXato(
            "Tasdiqlashdan keyin taqsimot 1C qoldig'idan kam bo'lib qoladi. Taqsimotni tekshiring."
        )
