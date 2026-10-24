"""1C HTTP-servisi (`/hs/av/`) uchun mijoz. Faqat GET, faqat o'qish."""
from datetime import datetime

import requests
from django.conf import settings

_VAQT_FORMATI = "%Y%m%d%H%M%S"


class OneCXato(Exception):
    """1C bilan aloqa xatosi. Matnda login/parol bo'lmaydi."""


class OneCClient:
    def __init__(self, base_url: str, login: str, parol: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.login = login
        self.parol = parol
        self.timeout = timeout

    @classmethod
    def settingsdan(cls) -> "OneCClient":
        return cls(settings.ONEC_URL, settings.ONEC_LOGIN, settings.ONEC_PAROL)

    def versiya(self) -> dict:
        return self._get("versiya")

    def spravochniklar(self) -> dict:
        return self._get("spravochniklar")

    def vositalar(self) -> dict:
        return self._get("vositalar")

    def harakatlar(self, dan: datetime, gacha: datetime) -> list[dict]:
        javob = self._get(
            "harakatlar",
            params={"dan": dan.strftime(_VAQT_FORMATI), "gacha": gacha.strftime(_VAQT_FORMATI)},
        )
        try:
            return javob["harakatlar"]
        except KeyError:
            raise OneCXato("1C javobida 'harakatlar' kaliti yo'q") from None

    def _get(self, yol: str, params: dict | None = None) -> dict:
        # Login/parol faqat Authorization sarlavhasida; URL va xato matniga chiqmaydi.
        # Asl istisno matni xatoga qo'shilmaydi (`from None`): unda URL/sarlavha bo'lishi mumkin.
        try:
            javob = requests.get(
                f"{self.base_url}/{yol}",
                params=params,
                auth=(self.login, self.parol),
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise OneCXato(f"1C javob bermadi ({self.timeout} s ichida): /{yol}") from None
        except requests.RequestException as xato:
            raise OneCXato(f"1C bilan ulanib bo'lmadi: /{yol} ({type(xato).__name__})") from None

        if javob.status_code != 200:
            raise OneCXato(f"1C HTTP {javob.status_code} qaytardi: /{yol}")
        try:
            malumot = javob.json()
        except ValueError:
            raise OneCXato(f"1C javobi JSON emas: /{yol}") from None
        if not isinstance(malumot, dict):
            raise OneCXato(f"1C javobi kutilgan shaklda emas: /{yol}")
        return malumot
