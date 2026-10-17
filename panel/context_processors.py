from hisoblar.huquqlar import huquqi_bor
from onec.sinxron import ketma_ket_xatolar, oxirgi_muvaffaqiyatli

XATO_CHEGARASI = 3


def sinxron_holati(request):
    """Barcha sahifalar uchun 1C sinxron holati: oxirgi muvaffaqiyatli vaqt va aloqa xatosi belgisi."""
    if not request.user.is_authenticated:
        return {}
    oxirgi = oxirgi_muvaffaqiyatli()
    return {
        "hisobot_huquqi": huquqi_bor(request.user, "hisobot"),
        "sozlama_huquqi": huquqi_bor(request.user, "sozlama"),
        "tozalash_huquqi": huquqi_bor(request.user, "tozalash"),
        "sinxron_holati": {
            "oxirgi": (oxirgi.tugadi or oxirgi.boshlandi) if oxirgi else None,
            "xato": ketma_ket_xatolar() >= XATO_CHEGARASI,
        }
    }
