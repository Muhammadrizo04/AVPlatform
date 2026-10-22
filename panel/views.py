from django.shortcuts import render
from django.utils import timezone

from hisobotlar.servis import filial_kesimi, jami
from hisoblar.huquqlar import amal_kerak, huquqi_bor
from vositalar.bayroqlar import BAYROQLAR, bayroq_sonlari

# Buxgalteriya tozalash vazifalarini ko'rmaydigan (pul huquqi yo'q) rol — HR — uchun faqat o'zi hal qiladigan bayroqlar:
# МОЛ biriktirish (akt orqali), ketgan xodimdagi AV'lar va bo'limsiz qatorlar.
XODIM_BAYROQLARI = ("molsiz", "ketgan_xodimda", "bolimsiz")


@amal_kerak("korish")
def bosh(request):
    bugun = timezone.localdate()
    kalitlar = None if huquqi_bor(request.user, "pul_korish") else XODIM_BAYROQLARI
    sonlar = bayroq_sonlari(request.user, bugun, kalitlar)
    bayroqlar = [{"kalit": k, "nomi": BAYROQLAR[k].nomi, "soni": sonlar[k]} for k in sonlar]
    filiallar = filial_kesimi(request.user, bugun)
    return render(
        request, "panel/bosh.html",
        {"filiallar": filiallar, "jami": jami(filiallar), "bayroqlar": bayroqlar},
    )
