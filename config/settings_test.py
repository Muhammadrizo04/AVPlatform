"""Testlar uchun sozlamalar: .env talab qilinmaydi (DEBUG standartlari ishlaydi)."""
import os

os.environ.setdefault("DEBUG", "True")

# Windows'da WeasyPrint Pango'ni MSYS2'dan oladi (Linux'da kerak emas).
_MSYS2 = r"C:\msys64\mingw64\bin"
if os.name == "nt" and os.path.isdir(_MSYS2):
    os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", _MSYS2)

from .settings import *  # noqa: E402,F401,F403
