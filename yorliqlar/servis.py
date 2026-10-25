"""QR-yorliqlar: sof yorliq mantig'i va PDF (WeasyPrint). QR matni: `DS|<filial kodi>|<inv. raqam>`."""
import base64
import io
import textwrap
from decimal import Decimal

import segno
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from jurnal.yoz import yoz
from onec.models import AV
from vositalar.models import AVKartochka, YorliqOlchami

BELGI_KOEFF = Decimal("0.55")
CHEKKA_MM = 1.5  # yorliq ichki chetlari
QR_BORDER = 2  # modullarda


def belgi_soni(olcham: YorliqOlchami) -> int:
    """Nom qatoridagi belgilar soni: `int(eni_mm × 0.55)`."""
    return int(olcham.eni_mm * BELGI_KOEFF)


def qisqa_nom(nomi: str, olcham: YorliqOlchami) -> list[str]:
    """Nomni ko'pi bilan 2 qatorga joylaydi (qatorda `belgi_soni` belgi); sig'masa oxiri `…`."""
    n = belgi_soni(olcham)
    nomi = " ".join((nomi or "").split())
    if not nomi:
        return []
    qatorlar = textwrap.wrap(nomi, width=n, break_long_words=True, break_on_hyphens=False)
    if len(qatorlar) <= 2:
        return qatorlar
    ikkinchi = (qatorlar[1] if len(qatorlar[1]) < n else qatorlar[1][: n - 1]).rstrip() + "…"
    return [qatorlar[0], ikkinchi]


def _qr(matn: str):
    return segno.make(matn, error="m", micro=False)


def qr_svg(matn: str) -> str:
    """PDF'ga joylanadigan QR (SVG, o'lchamsiz — `viewBox` bilan)."""
    buf = io.BytesIO()
    _qr(matn).save(buf, kind="svg", border=QR_BORDER, omitsize=True, xmldecl=False, svgns=True)
    return buf.getvalue().decode()


def qr_png(matn: str, scale: int = 8) -> bytes:
    """Aynan shu QR'ning PNG ko'rinishi (testda dekod qilish uchun)."""
    buf = io.BytesIO()
    _qr(matn).save(buf, kind="png", border=QR_BORDER, scale=scale)
    return buf.getvalue()


def _mm(qiymat: float) -> str:
    return f"{qiymat:.2f}"


def yorliq_pdf(elementlar: list[tuple[AV, int]], olcham: YorliqOlchami) -> bytes:
    """Har nusxa — alohida sahifa, sahifa o'lchami aynan `eni_mm × boyi_mm`. Kalitsiz AV → ValueError (PDF yaratilmaydi)."""
    kalitsiz = [av.nomi for av, _ in elementlar if av.kalit is None]
    if kalitsiz:
        raise ValueError("Inv. raqami yoki filial rekviziti yo'q AV'ga yorliq chop etib bo'lmaydi: " + ", ".join(kalitsiz))
    if not elementlar:
        raise ValueError("AV tanlanmagan.")
    if any(nusxa < 1 for _, nusxa in elementlar):
        raise ValueError("Nusxalar soni kamida 1 bo'lishi kerak.")

    from weasyprint import HTML  # kech import: Pango faqat PDF kerak bo'lganda yuklanadi

    eni, boyi = float(olcham.eni_mm), float(olcham.boyi_mm)
    qr = min(boyi - 4, eni * 0.5)
    nom_balandligi = boyi - 2 * CHEKKA_MM - qr - 0.5
    # Pastda nom uchun joy yetmasa (past yorliq), nom QR yonida, o'ng ustunda joylashadi.
    yonida = nom_balandligi < 4.0
    if yonida:
        kenglik, balandlik = eni - qr - 2 * CHEKKA_MM - 1, qr * 0.5
    else:
        kenglik, balandlik = eni - 2 * CHEKKA_MM, nom_balandligi
    # Nom shrifti: qator kengligiga (belgi_soni) va ajratilgan balandlikka (2 qator) moslanadi.
    shrift_pt = min(8.0, kenglik / max(belgi_soni(olcham), 1) / 0.62 * 2.835, balandlik / 2 / 1.15 * 2.835)
    yorliqlar = []
    for av, nusxa in elementlar:
        kalit = av.kalit
        rasm = "data:image/svg+xml;base64," + base64.b64encode(qr_svg(kalit).encode()).decode()
        yorliqlar.append(
            {
                "qr": rasm,
                "inv": av.inv_raqam.strip(),
                "filial": av.filial_rekvizit.nomi,
                "nom": qisqa_nom(av.nomi, olcham),
                "nusxa": nusxa,
            }
        )
    html = render_to_string(
        "yorliqlar/yorliq_pdf.html",
        {
            "eni": _mm(eni),
            "boyi": _mm(boyi),
            "qr": _mm(qr),
            "chekka": _mm(CHEKKA_MM),
            "nom_yonida": yonida,
            "nom_shrifti": f"{max(shrift_pt, 3.0):.2f}",
            "inv_shrifti": f"{min(max(boyi * 0.28, 7), 16):.2f}",
            "yorliqlar": [y for y in yorliqlar for _ in range(y["nusxa"])],
        },
    )
    return HTML(string=html).write_pdf()


def chop_etildi(avlar: list[AV], kim) -> None:
    """Chop etilgan yorliq kalitini saqlaydi (`yorliq_kaliti = av.kalit`, `yorliq_sana = now()`) va jurnalga yozadi."""
    with transaction.atomic():
        for av in avlar:
            kalit = av.kalit
            if kalit is None:
                raise ValueError(f"{av.nomi}: yorliq kaliti yo'q.")
            kartochka, _ = AVKartochka.objects.select_for_update().get_or_create(av=av)
            eski = kartochka.yorliq_kaliti
            kartochka.yorliq_kaliti = kalit
            kartochka.yorliq_sana = timezone.now()
            kartochka.save(update_fields=["yorliq_kaliti", "yorliq_sana"])
            yoz(kim, kartochka, "yorliq_kaliti", eski, kalit)
