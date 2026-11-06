"""AV turi sozlamasiga maydon qo'shish: turda bor kalit o'zgarmaydi, faqat yetishmagani qo'shiladi."""
import json

from jurnal.yoz import yoz

MAX_MAYDON = 50


def yetishmaganlarni_qosh(sozlama, maydonlar: list[dict], kim=None, kim_nomi: str | None = None) -> str:
    """Natija: `qoshildi`, `bor` (hammasi turda bor) yoki `sigmadi` (`MAX_MAYDON` dan oshadi, tur o'zgarmaydi)."""
    mavjud = {m["kalit"] for m in sozlama.maydonlar}
    yangilari = [m for m in maydonlar if m["kalit"] not in mavjud]
    if not yangilari:
        return "bor"
    if len(sozlama.maydonlar) + len(yangilari) > MAX_MAYDON:
        return "sigmadi"
    eski = json.dumps(sozlama.maydonlar, ensure_ascii=False)
    sozlama.maydonlar = [*sozlama.maydonlar, *yangilari]
    sozlama.save()
    yoz(kim, sozlama, "maydonlar", eski, json.dumps(sozlama.maydonlar, ensure_ascii=False), kim_nomi=kim_nomi)
    return "qoshildi"
