from hisoblar.huquqlar import huquqi_bor
from vositalar.models import Sozlama
from onec.sinxron import ketma_ket_xatolar, oxirgi_muvaffaqiyatli
from panel.vazifalar import kutayotgan_ishlar

XATO_CHEGARASI = 3


def sinxron_holati(request):
    """Barcha sahifalar uchun 1C sinxron holati: oxirgi muvaffaqiyatli vaqt va aloqa xatosi belgisi."""
    if not request.user.is_authenticated:
        return {}
    oxirgi = oxirgi_muvaffaqiyatli()
    # Kutayotgan ishlar (qo'ng'iroqcha) va menyudagi belgilar — HTMX bo'laklarida hisoblanmaydi
    ishlar = [] if request.headers.get("HX-Request") else kutayotgan_ishlar(request.user)
    chiqim_soni = sum(i["soni"] for i in ishlar if i["tur"] == "chiqim") or None
    return {
        "chiqim_huquqi": huquqi_bor(request.user, "chiqim_korish"),
        "chiqim_kutilmoqda_soni": chiqim_soni,
        "akt_qoralama_soni": sum(i["soni"] for i in ishlar if i["tur"] == "akt"),
        "kutayotgan_ishlar": ishlar,
        "kutayotgan_jami": sum(i["soni"] for i in ishlar),
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
