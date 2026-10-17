"""Testlar uchun sozlamalar: .env talab qilinmaydi (DEBUG standartlari ishlaydi)."""
import os

os.environ.setdefault("DEBUG", "True")

from .settings import *  # noqa: E402,F401,F403
