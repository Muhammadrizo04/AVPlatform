"""AV turi bo'yicha qo'shimcha maydonlarni tekshirish (spec §7.4). Toza funksiya: bazaga tegmaydi."""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

# «xotira» tipi (Storage): har qator — turi va hajmi; qiymat «M.2 SSD 512 GB + HDD 1 TB» ko'rinishida saqlanadi
XOTIRA_TURLARI = ("M.2 SSD", "SATA SSD", "HDD")
XOTIRA_HAJMLARI = ("128 GB", "256 GB", "512 GB", "1 TB", "2 TB", "4 TB")
XOTIRA_MAKS = 4
XOTIRA_AJRATGICH = " + "
# Shundan uzun tanlov ro'yxati kartochkada qidiruvli maydon bo'lib chiqadi (`i3` yozilsa — barcha i3 lar)
QIDIRUVLI_TANLOV = 15


def _son(matn: str) -> str:
    try:
        qiymat = Decimal(matn.replace(",", ".").replace(" ", ""))
    except InvalidOperation:
        raise ValueError("Son kiriting.")
    if not qiymat.is_finite():
        raise ValueError("Son kiriting.")
    return format(qiymat.normalize(), "f")


def _sana(matn: str) -> str:
    try:
        return date.fromisoformat(matn).isoformat()
    except ValueError:
        raise ValueError("Sanani YYYY-OO-KK ko'rinishida kiriting.")


def xotira_qatorlari(qiymat: str) -> list[tuple[str, str]]:
    """«M.2 SSD 512 GB + HDD 1 TB» -> [("M.2 SSD", "512 GB"), ("HDD", "1 TB")]; tanib bo'lmagan qism — ("", qism)."""
    natija = []
    for qism in (q.strip() for q in (qiymat or "").split(XOTIRA_AJRATGICH.strip())):
        if not qism:
            continue
        tur = next((t for t in XOTIRA_TURLARI if qism.startswith(t + " ")), "")
        natija.append((tur, qism[len(tur):].strip() if tur else qism))
    return natija


def _xotira(matn: str) -> str:
    qatorlar = xotira_qatorlari(matn)
    if len(qatorlar) > XOTIRA_MAKS:
        raise ValueError(f"ko'pi bilan {XOTIRA_MAKS} ta qurilma.")
    for tur, hajm in qatorlar:
        if tur not in XOTIRA_TURLARI or hajm not in XOTIRA_HAJMLARI:
            raise ValueError("har qator uchun turi va hajmini ro'yxatdan tanlang.")
    return XOTIRA_AJRATGICH.join(f"{tur} {hajm}" for tur, hajm in qatorlar)


def qoshimcha_tekshir(maydonlar: list[dict], qiymatlar: dict, eski: dict | None = None) -> dict:
    """`maydonlar` (AVTuriSozlama.maydonlar) bo'yicha `qiymatlar` ni tekshirib, tozalangan {kalit: matn} qaytaradi.
    Bo'sh qiymatlar tushirib qoldiriladi; sozlamada yo'q kalitlar e'tiborga olinmaydi. Xato bo'lsa — `ValidationError`
    ({maydon kaliti: [xabar]}). `eski` dagi bilan bir xil (o'zgarmagan) qiymat tekshirilmaydi — sozlama keyin
    qat'iylashsa (masalan, tanlov ro'yxati qo'shilsa), boshqa maydonlarni saqlash to'xtab qolmasin."""
    eski = eski or {}
    toza, xatolar = {}, {}
    for maydon in maydonlar:
        kalit, nomi, tip = maydon["kalit"], maydon.get("nomi") or maydon["kalit"], maydon.get("tip", "matn")
        qiymat = qiymatlar.get(kalit)
        qiymat = "" if qiymat is None else str(qiymat).strip()
        if not qiymat:
            if maydon.get("majburiy"):
                xatolar[kalit] = [f"«{nomi}» to'ldirilishi shart."]
            continue
        if qiymat == eski.get(kalit):
            toza[kalit] = qiymat
            continue
        try:
            if tip == "son":
                qiymat = _son(qiymat)
            elif tip == "sana":
                qiymat = _sana(qiymat)
            elif tip == "tanlov" and qiymat not in maydon.get("tanlov_qiymatlari", []):
                raise ValueError("Ro'yxatdan tanlang (o'zingiz yozgan qiymat qabul qilinmaydi).")
            elif tip == "xotira":
                qiymat = _xotira(qiymat)
        except ValueError as xato:
            xatolar[kalit] = [f"«{nomi}»: {xato}"]
            continue
        toza[kalit] = qiymat
    if xatolar:
        raise ValidationError(xatolar)
    return toza
