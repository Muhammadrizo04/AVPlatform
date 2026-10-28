from chiqimlar.models import ChiqimHujjat
from hisoblar.huquqlar import filial_bilan_chekla, huquqi_bor
from vositalar.models import Sozlama
from onec.sinxron import ketma_ket_xatolar, oxirgi_muvaffaqiyatli

XATO_CHEGARASI = 3


def sinxron_holati(request):
    """Barcha sahifalar uchun 1C sinxron holati: oxirgi muvaffaqiyatli vaqt va aloqa xatosi belgisi."""
    if not request.user.is_authenticated:
        return {}
    oxirgi = oxirgi_muvaffaqiyatli()
    chiqim_soni = None
    # Kutilayotgan chiqimlar belgisi — faqat ularni tasdiqlay oladiganlarga (HR va rahbar uchun vazifa emas).
    if huquqi_bor(request.user, "taqsimot") and not request.headers.get("HX-Request"):
        chiqim_soni = filial_bilan_chekla(
            ChiqimHujjat.objects.filter(holat__in=(ChiqimHujjat.Holat.KUTILMOQDA, ChiqimHujjat.Holat.BEKOR_1C)),
            request.user
        ).count()
    return {
        "chiqim_huquqi": huquqi_bor(request.user, "chiqim_korish"),
        "chiqim_kutilmoqda_soni": chiqim_soni,
        "hisobot_huquqi": huquqi_bor(request.user, "hisobot"),
        "pul_huquqi": huquqi_bor(request.user, "pul_korish"),
        "korish_huquqi": huquqi_bor(request.user, "korish"),
        "bosh_huquqi": huquqi_bor(request.user, "bosh_sahifa"),
        "reviziya_huquqi": huquqi_bor(request.user, "reviziya_korish"),
        "kompaniya_nomi": Sozlama.ol().kompaniya_nomi,
        "sozlama_huquqi": huquqi_bor(request.user, "sozlama"),
        "tozalash_huquqi": huquqi_bor(request.user, "tozalash"),
        "sinxron_holati": {
            "oxirgi": (oxirgi.tugadi or oxirgi.boshlandi) if oxirgi else None,
            "xato": ketma_ket_xatolar() >= XATO_CHEGARASI,
        }
    }
