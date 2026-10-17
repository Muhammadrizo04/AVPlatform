"""1C'dan sinxron: uchala javobni olib, `onec` nusxa jadvallarini bitta tranzaksiyada yangilaydi.

1C sanalari zonasiz Toshkent vaqti: bazaga joriy zona bilan `make_aware` qilib yoziladi,
1C'ga esa zonasiz mahalliy vaqt yuboriladi.
"""
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from vositalar.moslash import moslashtir

from .client import OneCClient
from .models import AV, AVQoldiq, AVTuri, Filial, Harakat1C, SinxronJurnal, Tashkilot, Xodim

logger = logging.getLogger(__name__)

QULF_KALITI = 7310001
HARAKAT_OYNASI = timedelta(days=45)
# To'liq sinxronda harakatlar shu sanadan olinadi (strftime 4 xonali yil beradi).
TOLIQ_BOSHI = datetime(1900, 1, 1)


class SinxronBand(Exception):
    """Boshqa sinxron ishlayapti (advisory lock band)."""


def sinxronla(client: OneCClient, toliq: bool = False, hozir: datetime | None = None) -> SinxronJurnal:
    """Bitta sinxron urinishi. Natija jurnalga yoziladi; band bo'lsa `SinxronBand` ko'tariladi."""
    boshlandi = timezone.now()
    hozir = hozir or boshlandi

    with connection.cursor() as kursor:
        kursor.execute("SELECT pg_try_advisory_lock(%s)", [QULF_KALITI])
        olindi = kursor.fetchone()[0]
    if not olindi:
        SinxronJurnal.objects.create(
            boshlandi=boshlandi, tugadi=timezone.now(), natija=SinxronJurnal.Natija.BAND, toliq=toliq
        )
        raise SinxronBand("Boshqa sinxron ishlayapti")

    try:
        try:
            ozgarishlar = _bajar(client, toliq, hozir, boshlandi)
        except Exception as xato:
            # atomic blok allaqachon rollback qilingan; jurnal alohida (autocommit) yoziladi.
            logger.exception("Sinxron xato bilan tugadi")
            return SinxronJurnal.objects.create(
                boshlandi=boshlandi, tugadi=timezone.now(), natija=SinxronJurnal.Natija.XATO,
                xato_matni=_maxfiysiz(f"{type(xato).__name__}: {xato}", client), toliq=toliq,
            )
        return SinxronJurnal.objects.create(
            boshlandi=boshlandi, tugadi=timezone.now(), natija=SinxronJurnal.Natija.OK,
            ozgarishlar=ozgarishlar, toliq=toliq,
        )
    finally:
        with connection.cursor() as kursor:
            kursor.execute("SELECT pg_advisory_unlock(%s)", [QULF_KALITI])


def oxirgi_muvaffaqiyatli() -> SinxronJurnal | None:
    return SinxronJurnal.objects.filter(natija=SinxronJurnal.Natija.OK).order_by("-boshlandi", "-id").first()


def ketma_ket_xatolar() -> int:
    """Oxirgi muvaffaqiyatli sinxrondan keyingi xatolar soni (`band` hisobga olinmaydi)."""
    natijalar = (
        SinxronJurnal.objects.exclude(natija=SinxronJurnal.Natija.BAND)
        .order_by("-boshlandi", "-id")
        .values_list("natija", flat=True)
    )
    son = 0
    for natija in natijalar.iterator():
        if natija != SinxronJurnal.Natija.XATO:
            break
        son += 1
    return son


def _bajar(client, toliq: bool, hozir: datetime, vaqt: datetime) -> dict:
    # 1C so'rovlari tranzaksiyadan oldin: tarmoq kutilayotganda baza qulflanmaydi.
    if toliq:
        dan = None
        dan_1c = TOLIQ_BOSHI
    else:
        dan = (hozir - HARAKAT_OYNASI).replace(microsecond=0)
        dan_1c = timezone.localtime(dan).replace(tzinfo=None)
    gacha_1c = timezone.localtime(hozir).replace(tzinfo=None, microsecond=0)

    sprav = client.spravochniklar()
    vos = client.vositalar()
    harakatlar = client.harakatlar(dan_1c, gacha_1c)

    ozgarishlar = {}
    with transaction.atomic():
        tashkilotlar = _upsert(Tashkilot, sprav["tashkilotlar"], _tashkilot, vaqt, ozgarishlar, "tashkilot")
        filiallar = _upsert(Filial, sprav["filiallar"], _filial, vaqt, ozgarishlar, "filial")
        turlar = _upsert(AVTuri, sprav["av_turlari"], _av_turi, vaqt, ozgarishlar, "av_turi")
        _upsert(
            Xodim, sprav["xodimlar"], lambda q: _xodim(q, filiallar), vaqt, ozgarishlar, "xodim"
        )
        avlar = _upsert(
            AV, vos["vositalar"], lambda q: _av(q, turlar, tashkilotlar, filiallar), vaqt, ozgarishlar, "av"
        )
        _qoldiqlar(vos["qoldiqlar"], avlar, tashkilotlar, filiallar, ozgarishlar)
        _harakatlar(harakatlar, dan, avlar, tashkilotlar, filiallar, ozgarishlar)
        ozgarishlar["moslash"] = moslashtir()
    return ozgarishlar


def _upsert(model, qatorlar, maydonlar, vaqt, ozgarishlar, kalit) -> dict:
    """Ref bo'yicha upsert. Kelmaganlar `onec_da_yoq=True` (o'chirilmaydi).

    `sinx_vaqti` — yozuv sinxron tomonidan oxirgi marta yaratilgan/o'zgartirilgan vaqt.
    Qaytaradi: shu javobda kelgan {ref: id}.
    """
    mavjud = {obj.ref_1c: obj for obj in model.objects.all()}
    yangilar, ozgarganlar, kelgan = [], [], {}
    for qator in qatorlar:
        ref = uuid.UUID(qator["ref"])
        qiymatlar = maydonlar(qator)
        obj = mavjud.get(ref)
        if obj is None:
            obj = model(ref_1c=ref, sinx_vaqti=vaqt, **qiymatlar)
            yangilar.append(obj)
        elif obj.onec_da_yoq or any(getattr(obj, k) != v for k, v in qiymatlar.items()):
            for k, v in qiymatlar.items():
                setattr(obj, k, v)
            obj.onec_da_yoq = False
            obj.sinx_vaqti = vaqt
            ozgarganlar.append(obj)
        kelgan[ref] = obj

    yoqolganlar = [obj for ref, obj in mavjud.items() if ref not in kelgan and not obj.onec_da_yoq]
    for obj in yoqolganlar:
        obj.onec_da_yoq = True
        obj.sinx_vaqti = vaqt

    model.objects.bulk_create(yangilar, batch_size=500)
    if ozgarganlar or yoqolganlar:
        maydon_nomlari = [f.attname for f in model._meta.concrete_fields if not f.primary_key]
        model.objects.bulk_update(ozgarganlar + yoqolganlar, maydon_nomlari, batch_size=500)

    ozgarishlar[kalit] = {
        "yaratildi": len(yangilar), "yangilandi": len(ozgarganlar), "yoqoldi": len(yoqolganlar)
    }
    return {ref: obj.pk for ref, obj in kelgan.items()}


def _tashkilot(q) -> dict:
    return {"nomi": _matn(q, "nomi")}


def _filial(q) -> dict:
    return {"kod": _matn(q, "kod"), "nomi": _matn(q, "nomi")}


def _av_turi(q) -> dict:
    return {"nomi": _matn(q, "nomi"), "tip": _matn(q, "tip")}


def _xodim(q, filiallar) -> dict:
    return {
        "ism": _matn(q, "ism"),
        "filial_id": _id(q.get("filial"), filiallar),
        "telefon": _matn(q, "telefon"),
        "ishdan_bushagan": bool(q.get("ishdan_bushagan")),
        "neaktiv": bool(q.get("neaktiv")),
        "ochirilgan": bool(q.get("ochirilgan")),
    }


def _av(q, turlar, tashkilotlar, filiallar) -> dict:
    sana = q.get("chiqarilgan_sana")
    return {
        "kod": _matn(q, "kod"),
        "nomi": _matn(q, "nomi"),
        "toliq_nomi": _matn(q, "toliq_nomi"),
        "inv_raqam": _matn(q, "inv_raqam"),
        "chiqarilgan_sana": date.fromisoformat(sana) if sana else None,
        "turi_id": _id(q.get("turi"), turlar),
        "tashkilot_id": _id(q.get("tashkilot"), tashkilotlar),
        "filial_rekvizit_id": _id(q.get("filial"), filiallar),
        "izoh_1c": _matn(q, "izoh"),
        "ochirilgan": bool(q.get("ochirilgan")),
    }


def _qoldiqlar(qatorlar, avlar, tashkilotlar, filiallar, ozgarishlar) -> None:
    """`AVQoldiq` to'liq almashtiriladi. Filiali bo'sh yoki AV'si noma'lum qator o'tkazib yuboriladi."""
    yangilar, otkazildi = [], 0
    for q in qatorlar:
        av_id = _id(q.get("av"), avlar)
        filial_id = _id(q.get("filial"), filiallar)
        if av_id is None or filial_id is None:
            otkazildi += 1
            continue
        yangilar.append(AVQoldiq(
            av_id=av_id, filial_id=filial_id, tashkilot_id=_id(q.get("tashkilot"), tashkilotlar),
            soni=_son(q.get("soni")), summa=_son(q.get("summa")),
        ))
    AVQoldiq.objects.all().delete()
    AVQoldiq.objects.bulk_create(yangilar, batch_size=500)
    ozgarishlar["qoldiq"] = len(yangilar)
    ozgarishlar["qoldiq_otkazildi"] = otkazildi


def _harakatlar(qatorlar, dan, avlar, tashkilotlar, filiallar, ozgarishlar) -> None:
    """`dan` dan boshlab (to'liqda — hammasi) o'chirilib qaytadan yoziladi.

    Sanasi/hujjati bo'sh yoki AV'si noma'lum qator o'tkazib yuboriladi.
    """
    zona = timezone.get_current_timezone()
    yangilar, otkazildi = [], 0
    for q in qatorlar:
        av_id = _id(q.get("av"), avlar)
        if not q.get("sana") or not q.get("hujjat_ref") or av_id is None:
            otkazildi += 1
            continue
        yangilar.append(Harakat1C(
            sana=timezone.make_aware(datetime.fromisoformat(q["sana"]), zona),
            hujjat_turi=_matn(q, "hujjat_turi"),
            hujjat_raqami=_matn(q, "hujjat_raqami"),
            hujjat_ref=uuid.UUID(q["hujjat_ref"]),
            av_id=av_id,
            tashkilot_id=_id(q.get("tashkilot"), tashkilotlar),
            filial_id=_id(q.get("filial"), filiallar),
            vid=q.get("vid"),
            soni=_son(q.get("soni")),
            summa=_son(q.get("summa")),
        ))
    eskilar = Harakat1C.objects.all() if dan is None else Harakat1C.objects.filter(sana__gte=dan)
    eskilar.delete()
    Harakat1C.objects.bulk_create(yangilar, batch_size=500)
    ozgarishlar["harakat"] = len(yangilar)
    ozgarishlar["harakat_otkazildi"] = otkazildi


def _id(ref, xarita) -> int | None:
    """1C ref -> shu sinxronda kelgan yozuv id'si; bo'sh yoki noma'lum bo'lsa None."""
    if not ref:
        return None
    return xarita.get(uuid.UUID(ref))


def _matn(q, kalit) -> str:
    return q.get(kalit) or ""


def _son(qiymat) -> Decimal:
    return Decimal(str(qiymat or 0))


def _maxfiysiz(matn: str, client) -> str:
    """Xato matnidan 1C login/parolni olib tashlaydi."""
    for maxfiy in (getattr(client, "parol", ""), getattr(client, "login", "")):
        if maxfiy:
            matn = matn.replace(maxfiy, "***")
    return matn
