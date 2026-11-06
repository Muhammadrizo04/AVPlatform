"""`python manage.py sahifa_tezligi <login> [url ...]` — sahifalarning server vaqti va SQL so'rovlari soni.

Ishchi serverda ham xavfsiz: hammasi bitta tranzaksiyada bajariladi va oxirida bekor qilinadi (sessiya, oxirgi kirish
vaqti va boshqa yozuvlar bazada qolmaydi). Faqat GET so'rovlari; 1C'ga murojaat qilinmaydi.
"""
import statistics
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext

SAHIFALAR = ["/", "/av/", "/av/bolimlar/", "/chiqimlar/", "/mol/", "/hisobotlar/kesim/", "/reviziya/"]
URINISH = 3


class _Bekor(Exception):
    """Tranzaksiyani ataylab bekor qilish uchun."""


class Command(BaseCommand):
    help = "Sahifalar tezligini o'lchaydi (bazaga hech narsa yozmaydi)"

    def add_arguments(self, parser):
        parser.add_argument("login", help="Qaysi foydalanuvchi nomidan ochiladi (rol va filial cheklovi uning)")
        parser.add_argument("url", nargs="*", help=f"Sahifalar (standart: {' '.join(SAHIFALAR)})")

    def handle(self, *args, login, url, **options):
        user = get_user_model().objects.filter(username=login).first()
        if user is None:
            raise CommandError(f"Foydalanuvchi topilmadi: {login}")
        host = next((h.lstrip(".") for h in settings.ALLOWED_HOSTS if h and h != "*"), "localhost")
        try:
            with transaction.atomic():
                client = Client(HTTP_HOST=host)
                client.force_login(user)
                for manzil in url or SAHIFALAR:
                    self._olch(client, manzil)
                raise _Bekor
        except _Bekor:
            pass

    def _olch(self, client, manzil):
        vaqtlar, holat, sorov = [], None, 0
        for _ in range(URINISH):
            with CaptureQueriesContext(connection) as q:
                boshi = time.perf_counter()
                javob = client.get(manzil, secure=getattr(settings, "SESSION_COOKIE_SECURE", False))
                vaqtlar.append((time.perf_counter() - boshi) * 1000)
            holat, sorov = javob.status_code, len(q)
        # Birinchi ochilish (kesh isishi) alohida, qolganlarining o'rtachasi — odatiy tezlik
        self.stdout.write(f"{manzil:32} {holat}  birinchi {vaqtlar[0]:6.0f} ms  odatiy {statistics.median(vaqtlar[1:]):6.0f} ms"
                          f"  SQL so'rovlari {sorov}")
