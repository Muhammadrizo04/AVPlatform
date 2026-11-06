"""Kartochkadagi qo'shimcha maydonlar bo'yicha qidiruv: «16 GB RAMli kompyuterlar nechta va qayerda?».

Asos — taqsimot qatorlari: ular har dona qaysi filial, bo'lim va javobgarda ekanini aytadi. Qiymatlar JSON'da erkin
yozilgani uchun taqqoslash Python'da, `qiymatlar()` bo'yicha (AV soni minglab, bir so'rov yetadi).
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from hisoblar.huquqlar import filial_bilan_chekla
from hisoblar.parametrlar import son
from hisobotlar.servis import _bolimlar
from onec.models import AV
from vositalar.models import AVKartochka, AVTuriSozlama, Holat, Taqsimot
from vositalar.qoshimcha import xotira_qatorlari

HAJM_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*([GT]B)\b", re.IGNORECASE)
NOL = Decimal(0)


@dataclass
class Natija:
    tanlangan: dict[str, str] = field(default_factory=dict)
    maydonlar: list[dict] = field(default_factory=list)  # {kalit, nomi, tip, variantlar: [(qiymat, dona)], tanlangan}
    qatorlar: list = field(default_factory=list)
    filiallar: list[tuple[str, Decimal]] = field(default_factory=list)
    jami: Decimal = NOL
    kiritilmagan: Decimal = NOL


def qiymatlar(tip: str, qiymat) -> set[str]:
    """Qidiruv uchun qiymatlar. «tanlov»da hajm guruhlanadi: «16 GB (8 + 8)» -> «16 GB»; Storage — har qatorning hajmi."""
    matn = str(qiymat or "").strip()
    if not matn:
        return set()
    if tip == "xotira":
        return {hajm for _, hajm in xotira_qatorlari(matn) if hajm}
    hajm = HAJM_RE.match(matn) if tip == "tanlov" else None
    return {f"{hajm[1]} {hajm[2].upper()}" if hajm else matn}


def _tartib(qiymat: str) -> tuple:
    """Hajmlar qiymati bo'yicha (8 GB, 16 GB, 1 TB), qolganlari alifbo bo'yicha."""
    hajm = HAJM_RE.match(qiymat)
    if hajm:
        return 0, float(hajm[1].replace(",", ".")) * (1024 if hajm[2].upper() == "TB" else 1), ""
    return 1, 0, qiymat.casefold()


def _sozlamalar() -> tuple[dict[str, dict], dict[int, set[str]]]:
    """(kalit -> maydon, turi_id -> shu turdagi kalitlar). Bir kalit bir necha turda bo'lsa — bitta maydon."""
    maydonlar, turlar = {}, {}
    for turi_id, royxat in AVTuriSozlama.objects.exclude(maydonlar=[]).values_list("av_turi_id", "maydonlar"):
        turlar[turi_id] = {m["kalit"] for m in royxat}
        for m in royxat:
            maydonlar.setdefault(m["kalit"], {"kalit": m["kalit"], "nomi": m["nomi"], "tip": m["tip"]})
    return maydonlar, turlar


def _qatorlar(user, params, turlar, maydonlar) -> list[Taqsimot]:
    qs = filial_bilan_chekla(
        Taqsimot.objects.filter(av__in=AV.objects.faol().values("pk"), av__turi_id__in=turlar, soni__gt=0), user
    ).select_related("av__turi", "filial", "mol").order_by("av__nomi", "filial__nomi", "pk")
    filial, turi = son(params.get("filial")), son(params.get("turi"))
    if filial is not None:
        qs = qs.filter(filial_id=filial)
    if turi is not None:
        qs = qs.filter(av__turi_id=turi)
    if params.get("holat") in Holat.values:
        qs = qs.filter(holat=params["holat"])
    qatorlar = list(qs)
    qoshimcha = dict(AVKartochka.objects.filter(av__in={t.av_id for t in qatorlar}).values_list("av_id", "qoshimcha"))
    bolimlar = _bolimlar()
    for t in qatorlar:
        t.bolim = bolimlar.get(t.bolim_id)
        t.xom = qoshimcha.get(t.av_id) or {}
        t.xususiyat = {k: qiymatlar(m["tip"], t.xom.get(k)) for k, m in maydonlar.items()}
    return qatorlar


def _mos(qator, shartlar: dict[str, str]) -> bool:
    return all(qiymat in qator.xususiyat[kalit] for kalit, qiymat in shartlar.items())


def _kiritilmagan(qator, shartlar: dict[str, str], turlar) -> bool:
    """Tanlangan xususiyat shu turda bor, lekin kiritilmagan; kiritilganlari esa tanlovga mos."""
    kalitlar = turlar[qator.av.turi_id]
    bosh = [k for k in shartlar if k in kalitlar and not qator.xususiyat[k]]
    return bool(bosh) and set(shartlar) <= kalitlar and _mos(qator, {k: v for k, v in shartlar.items() if k not in bosh})


def _variantlar(qatorlar, kalit: str, shartlar: dict[str, str]) -> list[tuple[str, Decimal]]:
    """Qolgan tanlovlarga mos qatorlardagi qiymatlar va dona soni: tanlov o'zgarsa, sonlar ham moslashadi."""
    boshqalar = {k: v for k, v in shartlar.items() if k != kalit}
    sanoq = Counter()
    for t in qatorlar:
        if _mos(t, boshqalar):
            for qiymat in t.xususiyat[kalit]:
                sanoq[qiymat] += t.soni
    return sorted(sanoq.items(), key=lambda juft: _tartib(juft[0]))


def qidir(user, params) -> Natija:
    maydonlar, turlar = _sozlamalar()
    tanlangan = {k: params[f"m_{k}"] for k in maydonlar if params.get(f"m_{k}")}
    qatorlar = _qatorlar(user, params, turlar, maydonlar)
    natija = Natija(tanlangan=tanlangan)
    for kalit, maydon in maydonlar.items():
        variantlar = _variantlar(qatorlar, kalit, tanlangan)
        if variantlar or kalit in tanlangan:
            natija.maydonlar.append({**maydon, "variantlar": variantlar, "tanlangan": tanlangan.get(kalit, "")})
    if not tanlangan:
        return natija
    natija.qatorlar = [t for t in qatorlar if _mos(t, tanlangan)]
    natija.jami = sum((t.soni for t in natija.qatorlar), NOL)
    natija.kiritilmagan = sum((t.soni for t in qatorlar if _kiritilmagan(t, tanlangan, turlar)), NOL)
    filiallar = Counter()
    for t in natija.qatorlar:
        filiallar[t.filial.nomi] += t.soni
    natija.filiallar = sorted(filiallar.items(), key=lambda juft: (-juft[1], juft[0]))
    return natija
