from django.shortcuts import render
from django.utils import timezone

from hisobotlar.servis import filial_kesimi
from hisoblar.huquqlar import amal_kerak
from vositalar.bayroqlar import BAYROQLAR, bayroq_sonlari


@amal_kerak("korish")
def bosh(request):
    bugun = timezone.localdate()
    sonlar = bayroq_sonlari(request.user, bugun)
    bayroqlar = [{"kalit": k, "nomi": b.nomi, "soni": sonlar[k]} for k, b in BAYROQLAR.items()]
    return render(request, "panel/bosh.html", {"filiallar": filial_kesimi(request.user, bugun), "bayroqlar": bayroqlar})
