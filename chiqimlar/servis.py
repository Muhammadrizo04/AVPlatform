"""1C chiqim harakatlaridan `ChiqimHujjat` yozuvlarini yaratish/yangilash/bekor qilish, tur taxmini va tasdiqlash."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from jurnal import yoz as jurnal_yoz
from onec.models import AVQoldiq, Harakat1C
from vositalar.amallar import AmalXato, _ozgartir, ayir_va_yoz, holat_ozgartir, kochir, qosh_va_yoz
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
    stat = {"yaratildi": 0, "yangilandi": 0, "bekor": 0, "qaytdi": 0, "bekor_1c": 0}
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
            elif c.holat == ChiqimHujjat.Holat.BEKOR_1C:
                # 1C'da qayta o'tkazildi, tasdiq hali qaytarilmagan — yana tasdiqlangan (taqsimot o'zgarmagan)
                c.holat = ChiqimHujjat.Holat.TASDIQLANGAN
                c.save(update_fields=["holat"])
                jurnal_yoz.yoz(None, c, "holat", ChiqimHujjat.Holat.BEKOR_1C, ChiqimHujjat.Holat.TASDIQLANGAN)
                stat["qaytdi"] += 1

        _taxminlarni_yangila(quyi, gacha, guruhlar)

        for kalit, c in mavjud.items():
            if kalit not in guruhlar and c.holat == ChiqimHujjat.Holat.KUTILMOQDA:
                c.holat = ChiqimHujjat.Holat.BEKOR
                c.save(update_fields=["holat"])
                jurnal_yoz.yoz(None, c, "holat", ChiqimHujjat.Holat.KUTILMOQDA, ChiqimHujjat.Holat.BEKOR)
                stat["bekor"] += 1
            elif kalit not in guruhlar and c.holat == ChiqimHujjat.Holat.TASDIQLANGAN:
                # Tasdiqlangandan keyin 1C'da bekor qilindi: taqsimotdan ayirilgan donalar endi «taqsimlanmagan» ga
                # qaytadi (moslash) — hisobchiga xabar, «Tasdiqni qaytarish» ularni asl joyiga qo'yadi.
                c.holat = ChiqimHujjat.Holat.BEKOR_1C
                c.save(update_fields=["holat"])
                jurnal_yoz.yoz(None, c, "holat", ChiqimHujjat.Holat.TASDIQLANGAN, ChiqimHujjat.Holat.BEKOR_1C)
                stat["bekor_1c"] += 1
    return stat


def _taxminlarni_yangila(quyi: datetime, gacha: datetime, guruhlar: dict) -> None:
    """Tur taxmini keyin kelgan kirim (B'dagi sinxron kechikishi) bilan o'zgarishi mumkin: `kutilmoqda` yozuvlar
    (guruhlardagilar va ±oynasi qayta yuklangan oraliqqa tegadiganlar) uchun taxmin qayta hisoblanadi. Jurnalga yozilmaydi."""
    shart = Q(sana__gte=quyi - TAXMIN_OYNASI, sana__lte=gacha + TAXMIN_OYNASI)
    for ref, av_id, filial_id in guruhlar:
        shart |= Q(hujjat_ref=ref, av_id=av_id, filial_id=filial_id)
    for c in ChiqimHujjat.objects.filter(holat=ChiqimHujjat.Holat.KUTILMOQDA).filter(shart):
        tur, _ = taxmin_qil(c.av_id, c.filial_id, c.sana, c.hujjat_turi)
        if tur != c.taxmin_tur:
            c.taxmin_tur = tur
            c.save(update_fields=["taxmin_tur"])


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
) -> Decimal:
    """Kutilayotgan 1C chiqimini tasdiqlaydi (spec §6.5): A filialdagi tanlangan qatorlardan jami `chiqim.soni` dona
    olib tashlanadi; `otkazish`da B'ga kelgan taqsimlanmagan donalar ixtiyoriy ravishda `b_bolim`ga joylanadi.

    `qatorlar` — {taqsimot_pk: soni} (0 lar e'tiborsiz); `kutilgan_soni` — forma ko'rsatgan chiqim soni.
    Qulf tartibi `moslashtir` bilan bir xil (ChiqimHujjat -> Taqsimot pk tartibida) — deadlock bo'lmaydi.
    Arxiv AV ham tasdiqlanadi (A juft uchun arxiv tekshiruvi yo'q). Xatoda `ChiqimXato`, tranzaksiya qaytariladi.
    Qaytaradi: B'ga joylangan donalar soni (joylash so'ralmagan yoki imkonsiz bo'lsa 0)."""
    joylandi = NOL
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

        hujjat_izoh = _izoh(c)
        c.ayirilganlar = [
            {"bolim": q.bolim_id, "mol": q.mol_id, "holat": q.holat, "soni": f"{soni:.3f}"} for q, soni in tanlangan
        ]
        for qator, soni in tanlangan:
            ayir_va_yoz(qator, soni, kim, _SABAB[tur], hujjat_izoh)

        eski = (c.holat, c.tur, c.qabul_filial_id, c.izoh)
        c.holat = ChiqimHujjat.Holat.TASDIQLANGAN
        c.tur = tur
        c.qabul_filial = qabul_filial
        c.izoh = izoh
        c.kim = kim
        c.qachon = timezone.now()
        c.save(update_fields=["holat", "tur", "qabul_filial", "izoh", "kim", "qachon", "ayirilganlar"])
        for maydon, oldingi, yangi in zip(
            ("holat", "tur", "qabul_filial", "izoh"), eski, (c.holat, c.tur, c.qabul_filial_id, c.izoh)
        ):
            if oldingi != yangi:
                jurnal_yoz.yoz(kim, c, maydon, oldingi, yangi)

        if b_bolim is not None:
            joylandi = _b_ga_joyla(c, qulflangan, qabul_filial, b_bolim, b_holat, kim)

        _tekshir_invariant(c)
    chiqim.refresh_from_db()
    return joylandi


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


def _b_ga_joyla(c: ChiqimHujjat, qulflangan: list, qabul_filial, b_bolim, b_holat: str, kim) -> Decimal:
    """B'dagi taqsimlanmagan qatordan min(chiqim soni, qator soni) donani `b_bolim`ga ko'chiradi; `b_holat` berilsa —
    aynan shu donalarning holati o'zgaradi. Taqsimlanmagan qator bo'lmasa — hech narsa qilinmaydi (Review Focus 5). Joylangan donalar sonini qaytaradi."""
    qator = next(
        (
            t for t in qulflangan
            if t.filial_id == qabul_filial.pk and t.bolim_id is None and t.mol_id is None
            and t.holat == Holat.ISHLATILMOQDA
        ),
        None,
    )
    if qator is None:
        return NOL
    soni = min(c.soni, qator.soni)
    try:
        nishon = kochir(qator, soni, b_bolim, kim)
        if b_holat and b_holat != nishon.holat:
            holat_ozgartir(nishon, soni, b_holat, kim)
    except AmalXato as xato:
        raise ChiqimXato(str(xato)) from None
    return soni


def _izoh(c: ChiqimHujjat) -> str:
    return f"{c.hujjat_turi} {c.hujjat_raqami}".strip()


def _ayirilganlar(c: ChiqimHujjat) -> list[tuple[tuple, Decimal]]:
    """Tasdiqlashda ayirilgan [((bolim_id, mol_id, holat), soni)]. Eski tasdiqlar (maydon bo'sh) — shu tasdiqning
    taqsimot harakatlaridan."""
    if c.ayirilganlar:
        return [((a["bolim"], a["mol"], a["holat"]), Decimal(a["soni"])) for a in c.ayirilganlar]
    harakatlar = TaqsimotHarakat.objects.filter(
        av_id=c.av_id, filial_id=c.filial_id, sabab=_SABAB.get(c.tur, ""), hujjat_izoh=_izoh(c)[:255],
        sana__gte=(c.qachon or c.sana) - timedelta(minutes=1),
    ).order_by("pk")
    return [((h.eski_bolim_id, h.eski_mol_id, h.eski_holat), h.soni) for h in harakatlar]


def tasdiqni_qaytar(chiqim: ChiqimHujjat, kim) -> str:
    """Tasdiqni qaytaradi — ayirilgan donalar asl (bo'lim, javobgar shaxs, holat) qatorlariga qaytadi:

    * `tasdiqlangan` (hujjat 1C'da bor; xato tasdiqni tuzatish) — donalar qo'shiladi, chiqim yana `kutilmoqda`
      (K oshadi, invariant saqlanadi) va qaytadan tasdiqlanadi;
    * `bekor_1c` (1C'da bekor qilingan) — donalar moslash qo'ygan «taqsimlanmagan» qatordan asl joyiga ko'chiriladi,
      chiqim `bekor`.

    Otkazishda qabul qiluvchi filialdagi joylash qaytarilmaydi (u 1C qoldig'i bilan moslash orqali to'g'rilanadi).
    Yangi holatni qaytaradi; xatoda `ChiqimXato`, tranzaksiya qaytariladi."""
    with transaction.atomic():
        c = ChiqimHujjat.objects.select_for_update().filter(pk=chiqim.pk).first()
        if c is None:
            raise ChiqimXato("Chiqim topilmadi. Sahifani yangilang.")
        if c.holat not in (ChiqimHujjat.Holat.TASDIQLANGAN, ChiqimHujjat.Holat.BEKOR_1C):
            raise ChiqimXato("Faqat tasdiqlangan yoki 1C'da bekor qilingan chiqimning tasdig'ini qaytarish mumkin.")
        qulflangan = list(
            Taqsimot.objects.select_for_update().filter(av_id=c.av_id, filial_id=c.filial_id).order_by("pk")
        )
        ayirilgan = _ayirilganlar(c)
        if not ayirilgan:
            raise ChiqimXato("Tasdiqda qaysi qatorlardan ayirilgani topilmadi — AV kartochkasida qo'lda tuzating.")
        izoh = f"{_izoh(c)} — tasdiq qaytarildi"
        Sabab = TaqsimotHarakat.Sabab
        if c.holat == ChiqimHujjat.Holat.TASDIQLANGAN:
            for joy, soni in ayirilgan:
                qosh_va_yoz(c.av_id, c.filial_id, joy, soni, kim, Sabab.CHIQIM_QAYTARILDI, izoh)
            yangi = ChiqimHujjat.Holat.KUTILMOQDA
        else:
            taqsimlanmagan = [
                t for t in qulflangan if t.bolim_id is None and t.mol_id is None and t.holat == Holat.ISHLATILMOQDA
            ]
            kerak = sum((s for joy, s in ayirilgan if joy != (None, None, Holat.ISHLATILMOQDA)), NOL)
            if sum((t.soni for t in taqsimlanmagan), NOL) < kerak:
                raise ChiqimXato(
                    "«Bo'limsiz» (taqsimlanmagan) qatorda qaytariladigan donalar yetarli emas — ular allaqachon "
                    "joylashtirilgan bo'lishi mumkin. AV kartochkasida qo'lda tuzating."
                )
            try:
                for joy, soni in ayirilgan:
                    if joy == (None, None, Holat.ISHLATILMOQDA):
                        continue
                    qoldi = soni
                    for manba in taqsimlanmagan:
                        t = Taqsimot.objects.filter(pk=manba.pk).first()  # oldingi ko'chirishda tugagan bo'lishi mumkin
                        if qoldi <= 0 or t is None:
                            continue
                        m = min(t.soni, qoldi)
                        _ozgartir(t, m, kim, Sabab.CHIQIM_QAYTARILDI, bolim=joy[0], mol=joy[1], holat=joy[2],
                                  hujjat_izoh=izoh)
                        qoldi -= m
            except AmalXato as xato:
                raise ChiqimXato(str(xato)) from None
            yangi = ChiqimHujjat.Holat.BEKOR
        eski = c.holat
        c.holat = yangi
        if yangi == ChiqimHujjat.Holat.KUTILMOQDA:
            c.tur, c.qabul_filial, c.kim, c.qachon, c.ayirilganlar = "", None, None, None, []
        c.save(update_fields=["holat", "tur", "qabul_filial", "kim", "qachon", "ayirilganlar"])
        jurnal_yoz.yoz(kim, c, "holat", eski, yangi)
        _tekshir_invariant(c)
    chiqim.refresh_from_db()
    return yangi


def _son(soni: Decimal) -> str:
    """1.000 -> «1», 2.500 -> «2.5» (tarix matni uchun)."""
    return format(soni.normalize(), "f")


# Umumiy tarix filtri: amal -> (nomi, [(eski, yangi) holat juftlari])
H = ChiqimHujjat.Holat
AMALLAR = {
    "tasdiq": ("Tasdiqlandi", [(H.KUTILMOQDA, H.TASDIQLANGAN)]),
    "tasdiq_bekor": ("Tasdiq bekor qilindi", [(H.TASDIQLANGAN, H.KUTILMOQDA)]),
    "bekor_1c": ("1C'da bekor qilindi", [(H.TASDIQLANGAN, H.BEKOR_1C)]),
    "qaytarildi": ("Tasdiq qaytarildi (1C bekori)", [(H.BEKOR_1C, H.BEKOR)]),
}


def holat_matni(eski: str, yangi: str) -> str:
    """Chiqim holati o'zgarishining odamga tushunarli nomi (tarix uchun)."""
    if (eski, yangi) == (H.KUTILMOQDA, H.TASDIQLANGAN):
        return "Tasdiqlandi"
    if (eski, yangi) == (H.TASDIQLANGAN, H.KUTILMOQDA):
        return "Tasdiq bekor qilindi — qayta tasdiqlash kutilmoqda"
    if (eski, yangi) == (H.TASDIQLANGAN, H.BEKOR_1C):
        return "1C'da hujjat bekor qilindi — tasdiqni qaytarish kerak"
    if (eski, yangi) == (H.BEKOR_1C, H.BEKOR):
        return "Tasdiq qaytarildi — donalar asl joyiga qo'yildi"
    holatlar = dict(H.choices)
    return f"Holat: {holatlar.get(eski, eski)} → {holatlar.get(yangi, yangi)}"


def chiqim_tarixi(c: ChiqimHujjat) -> list[dict]:
    """Chiqim tarixi (vaqt bo'yicha): 1C'dan kelishi, holat o'zgarishlari (kim — foydalanuvchi yoki «1C sinxron»)
    va shu hujjat bo'yicha taqsimot harakatlari (qaysi bo'lim / javobgar shaxs / holatdan qancha). [{vaqt, kim, matn}]"""
    from jurnal.models import Jurnal

    holat_nomi = dict(Holat.choices)
    tarix = [{"vaqt": c.yaratildi, "kim": "1C sinxron",
              "matn": f"1C'dan keldi: {_izoh(c)}, {_son(c.soni)} dona (taxmin: {c.get_taxmin_tur_display()})"}]
    for j in Jurnal.objects.filter(obyekt_turi="chiqimlar.chiqimhujjat", obyekt_id=str(c.pk), maydon="holat"):
        tarix.append({"vaqt": j.qachon, "kim": j.kim_nomi, "matn": holat_matni(j.eski, j.yangi)})
    harakatlar = (
        TaqsimotHarakat.objects.filter(av_id=c.av_id, filial_id=c.filial_id, hujjat_izoh__startswith=_izoh(c)[:255])
        .select_related("eski_bolim", "eski_mol", "yangi_bolim", "yangi_mol", "kim")
    )
    for h in harakatlar:
        if h.yangi_holat:  # qaytarish — qatorga qo'shildi
            joy = h.yangi_bolim.toliq_nomi if h.yangi_bolim else "Bo'limsiz"
            mol = f", {h.yangi_mol.ism}" if h.yangi_mol else ""
            matn = f"Qaytarildi: {joy}{mol}, {holat_nomi.get(h.yangi_holat, h.yangi_holat)} — +{_son(h.soni)} dona"
        else:
            joy = h.eski_bolim.toliq_nomi if h.eski_bolim else "Bo'limsiz"
            mol = f", {h.eski_mol.ism}" if h.eski_mol else ""
            matn = f"Ayirildi ({h.get_sabab_display()}): {joy}{mol}, {holat_nomi.get(h.eski_holat, h.eski_holat)} — −{_son(h.soni)} dona"
        tarix.append({"vaqt": h.sana, "kim": (h.kim.get_full_name() or h.kim.get_username()) if h.kim else "1C sinxron",
                      "matn": matn})
    return sorted(tarix, key=lambda t: t["vaqt"])


def _tekshir_invariant(c: ChiqimHujjat) -> None:
    """A juft: Σ taqsimot >= max(1C, 0) + K (qolgan kutilayotganlar); kam bo'lsa — `ChiqimXato`."""
    qoldiq = AVQoldiq.objects.filter(av_id=c.av_id, filial_id=c.filial_id).aggregate(s=Sum("soni"))["s"] or NOL
    taqsimot = Taqsimot.objects.filter(av_id=c.av_id, filial_id=c.filial_id).aggregate(s=Sum("soni"))["s"] or NOL
    k = kutilayotgan(Q(av_id=c.av_id, filial_id=c.filial_id)).get((c.av_id, c.filial_id), NOL)
    if taqsimot < max(qoldiq, NOL) + k:
        raise ChiqimXato(
            "Tasdiqlashdan keyin taqsimot 1C qoldig'idan kam bo'lib qoladi. Taqsimotni tekshiring."
        )
