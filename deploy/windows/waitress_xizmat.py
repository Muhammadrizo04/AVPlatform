"""«AV-platforma» Windows xizmati (NSSM) ishga tushiradigan waitress.

IIS (ARR) 127.0.0.1 dan proksi qiladi: X-Forwarded-For va X-Forwarded-Proto faqat undan qabul qilinadi.
waitress 3 bu sarlavhalarni ishonchli proksi berilmasa o'chirib tashlaydi — unda Django so'rovni HTTPS deb
bilmaydi (HSTS yo'q) va axes barcha mijozlarni 127.0.0.1 deb ko'radi. Parametrlar shu faylda, chunki
`waitress-serve` ga bo'sh joyli qiymatni NSSM orqali uzatish ishonchsiz.
"""
import os
import sys
from pathlib import Path

ILOVA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ILOVA))
os.chdir(ILOVA)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from waitress import serve  # noqa: E402

from config.wsgi import application  # noqa: E402

if __name__ == "__main__":
    serve(
        application,
        listen=f"127.0.0.1:{os.environ.get('AV_ICHKI_PORT', '8000')}",
        threads=8,
        channel_timeout=130,  # admin «Hozir sinxronlash» so'rov ichida (1C 60 s, IIS proksi 120 s)
        trusted_proxy="127.0.0.1",
        trusted_proxy_count=1,
        trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto"},
        ident="AV",
    )
