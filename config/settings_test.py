"""Testlar uchun sozlamalar: .env talab qilinmaydi (DEBUG standartlari ishlaydi)."""
import os
import tempfile

os.environ.setdefault("DEBUG", "True")
# Ishchi serverda `.env` da HTTPS, proksi va domen sozlamalari bor — testlar ularsiz (oddiy HTTP test klienti) ishlaydi.
# Qiymat bo'sh/False qilib qo'yiladi: settings.py `.env` ni o'qiganda muhitdagi qiymat ustun.
for _kalit, _qiymat in {"HTTPS": "False", "PROXY_ORQASIDA": "False", "CSRF_TRUSTED_ORIGINS": "", "ALLOWED_HOSTS": ""}.items():
    os.environ[_kalit] = _qiymat
# Test rasmlari hech qachon ishchi media papkasiga tushmasin
os.environ["MEDIA_ROOT"] = os.path.join(tempfile.gettempdir(), "av_test_media")

# Windows'da WeasyPrint Pango'ni MSYS2'dan oladi (Linux'da kerak emas).
_MSYS2 = r"C:\msys64\mingw64\bin"
if os.name == "nt" and os.path.isdir(_MSYS2):
    os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", _MSYS2)

from .settings import *  # noqa: E402,F401,F403

# Testlarni tezlatish: parol hesh'i (PBKDF2 ~0.3 s/login) o'rniga MD5. Faqat testlarda; ishchi settings.py o'zgarmaydi.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
