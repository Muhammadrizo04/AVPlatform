"""`python manage.py sinxron [--toliq]` — 1C'dan sinxron (systemd timer har 5 daqiqada, kechasi --toliq)."""
import time

from django.core.management.base import BaseCommand, CommandError

from onec.client import OneCClient
from onec.models import SinxronJurnal
from onec.sinxron import SinxronBand, sinxronla

# To'liq sinxron band bo'lsa (masalan, 5 daqiqalik sinxron ayni paytda ishlayapti) — shu oraliqda qayta urinadi.
TOLIQ_KUTISH_S = 15
TOLIQ_KUTISH_JAMI_S = 5 * 60


class Command(BaseCommand):
    help = "1C'dan ma'lumotlarni sinxronlash"

    def add_arguments(self, parser):
        parser.add_argument(
            "--toliq", action="store_true", help="Barcha harakatlarni to'liq qayta olish (45 kunlik oyna o'rniga)"
        )

    def handle(self, *args, toliq=False, **options):
        client = OneCClient.settingsdan()
        urinishlar = TOLIQ_KUTISH_JAMI_S // TOLIQ_KUTISH_S if toliq else 0
        while True:
            try:
                jurnal = sinxronla(client, toliq=toliq)
                break
            except SinxronBand:
                if urinishlar <= 0:
                    # Band — xato emas: keyingi navbatda yana urinadi.
                    self.stdout.write("Sinxron band: boshqa sinxron ishlayapti, bu safar o'tkazib yuborildi.")
                    return
                # To'liq sinxron kechada bir marta: o'tkazib yubormaslik uchun band tugashini kutadi.
                urinishlar -= 1
                self.stdout.write(f"Sinxron band, {TOLIQ_KUTISH_S} s dan keyin qayta urinadi.")
                time.sleep(TOLIQ_KUTISH_S)
        if jurnal.natija == SinxronJurnal.Natija.XATO:
            raise CommandError(f"Sinxron xato bilan tugadi: {jurnal.xato_matni}")
        self.stdout.write(self.style.SUCCESS(f"Sinxron muvaffaqiyatli tugadi: {jurnal.ozgarishlar}"))
