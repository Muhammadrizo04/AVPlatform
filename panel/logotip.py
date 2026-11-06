"""Logotip PDF'larga fayl ichida joylanadi: WeasyPrint uchun static URL yoki collectstatic kerak emas."""
import base64
from functools import lru_cache
from pathlib import Path

FAYL = Path(__file__).resolve().parent / "static" / "panel" / "logotip.png"


@lru_cache(maxsize=1)
def logotip_uri() -> str:
    return "data:image/png;base64," + base64.b64encode(FAYL.read_bytes()).decode()
