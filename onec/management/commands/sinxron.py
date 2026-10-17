"""`python manage.py sinxron [--toliq]` — 1C'dan sinxron (systemd timer har 5 daqiqada, kechasi --toliq)."""
from django.core.management.base import BaseCommand, CommandError

from onec.client import OneCClient
from onec.models import SinxronJurnal
from onec.sinxron import SinxronBand, sinxronla


class Command(BaseCommand):
    help = "1C'dan ma'lumotlarni sinxronlash"

    def add_arguments(self, parser):
        parser.add_argument(
            "--toliq", action="store_true", help="Barcha harakatlarni to'liq qayta olish (45 kunlik oyna o'rniga)"
        )

    def handle(self, *args, toliq=False, **options):
        try:
            jurnal = sinxronla(OneCClient.settingsdan(), toliq=toliq)
        except SinxronBand:
            # Band — xato emas: keyingi navbatda yana urinadi.
            self.stdout.write("Sinxron band: boshqa sinxron ishlayapti, bu safar o'tkazib yuborildi.")
            return
        if jurnal.natija == SinxronJurnal.Natija.XATO:
            raise CommandError(f"Sinxron xato bilan tugadi: {jurnal.xato_matni}")
        self.stdout.write(self.style.SUCCESS(f"Sinxron muvaffaqiyatli tugadi: {jurnal.ozgarishlar}"))
