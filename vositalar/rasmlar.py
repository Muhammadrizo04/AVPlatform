"""AV rasmlarini qabul qilish: haqiqiy rasm ekanini Pillow bilan tekshirish, kichraytirish, miniatyura."""
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Rasm

MAKS_HAJM = 15 * 1024 * 1024
MAKS_TOMON = 1600
MINI_TOMON = 300
MAKS_PIKSEL = 60_000_000  # dekompressiya bombasidan himoya
FORMATLAR = {"JPEG": "jpg", "PNG": "png"}
XATO = "Faqat JPEG yoki PNG rasm yuklash mumkin."


def _ochib_tekshir(fayl) -> tuple[Image.Image, str]:
    """Fayl haqiqatan JPEG/PNG rasm bo'lsa — (EXIF yo'nalishi qo'llangan rasm, format)."""
    try:
        fayl.seek(0)
        rasm = Image.open(fayl)
        if rasm.format not in FORMATLAR:
            raise ValidationError(XATO)
        if rasm.width * rasm.height > MAKS_PIKSEL:
            raise ValidationError("Rasm o'lchami juda katta.")
        format = rasm.format
        rasm.load()
        return ImageOps.exif_transpose(rasm), format
    except ValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError(XATO)


def _baytlar(rasm: Image.Image, format: str) -> bytes:
    buf = io.BytesIO()
    if format == "JPEG" and rasm.mode not in ("RGB", "L"):
        rasm = rasm.convert("RGB")
    rasm.save(buf, format, **({"quality": 85, "optimize": True} if format == "JPEG" else {"optimize": True}))
    return buf.getvalue()


def rasm_saqla(av, fayl, kim) -> Rasm:
    """Rasmni tekshirib, 1600 px gacha kichraytirib va 300 px miniatyura bilan saqlaydi. AV'ning birinchi rasmi
    asosiy bo'ladi. Noto'g'ri fayl — `ValidationError`."""
    if fayl.size > MAKS_HAJM:
        raise ValidationError("Rasm hajmi 15 MB dan oshmasligi kerak.")
    asl, format = _ochib_tekshir(fayl)
    ext = FORMATLAR[format]

    katta = asl.copy()
    katta.thumbnail((MAKS_TOMON, MAKS_TOMON))
    mini = asl.copy()
    mini.thumbnail((MINI_TOMON, MINI_TOMON))
    nom = f"{uuid.uuid4().hex}.{ext}"

    with transaction.atomic():
        birinchi = not Rasm.objects.select_for_update().filter(av=av).exists()
        rasm = Rasm(av=av, kim=kim, asosiy=birinchi)
        rasm.fayl.save(nom, ContentFile(_baytlar(katta, format)), save=False)
        rasm.miniatyura.save(nom, ContentFile(_baytlar(mini, format)), save=False)
        rasm.save()
    return rasm
