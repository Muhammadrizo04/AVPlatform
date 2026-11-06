"""AV turi qo'shimcha maydonlarini JSON fayldan bazaga qo'shadi. Sozlamalar bazada saqlanadi, `git pull` ularni olib bormaydi.

Tur `ref_1c` bo'yicha, topilmasa nomi yagona bo'lsa nomi bo'yicha aniqlanadi. Qayta ishga tushirish xavfsiz.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from onec.models import AVTuri
from vositalar.models import AVTuriSozlama
from vositalar.turi_maydonlari import yetishmaganlarni_qosh

KIM_NOMI = "Buyruq: turi_maydonlarini_yukla"


def _tur(yozuv: dict) -> AVTuri | None:
    tur = AVTuri.objects.filter(ref_1c=yozuv["ref_1c"]).first()
    if tur:
        return tur
    nomdoshlar = list(AVTuri.objects.filter(nomi=yozuv["nomi"])[:2])
    return nomdoshlar[0] if len(nomdoshlar) == 1 else None


class Command(BaseCommand):
    help = "AV turi qo'shimcha maydonlarini fayldan qo'shadi (bor maydonlar o'zgarmaydi)."

    def add_arguments(self, parser):
        parser.add_argument("fayl", nargs="?", default=str(Path(settings.BASE_DIR) / "deploy" / "turi_maydonlari.json"))

    def handle(self, *args, fayl, **kwargs):
        turlar = json.loads(Path(fayl).read_text(encoding="utf8"))
        with transaction.atomic():
            for yozuv in turlar:
                self.stdout.write(self._yukla(yozuv))

    def _yukla(self, yozuv: dict) -> str:
        tur = _tur(yozuv)
        if tur is None:
            return f"{yozuv['nomi']}: tur topilmadi, o'tkazib yuborildi."
        sozlama, _ = AVTuriSozlama.objects.get_or_create(av_turi=tur)
        oldin = len(sozlama.maydonlar)
        natija = yetishmaganlarni_qosh(sozlama, yozuv["maydonlar"], kim_nomi=KIM_NOMI)
        if natija == "qoshildi":
            return f"{tur.nomi}: {len(sozlama.maydonlar) - oldin} ta maydon qo'shildi."
        if natija == "bor":
            return f"{tur.nomi}: maydonlar allaqachon bor."
        return f"{tur.nomi}: maydonlar soni chegaradan oshgani uchun sig'madi."
