"""«Kutayotgan ishlar»: foydalanuvchi bajarishi kerak bo'lgan ishlar soni (tepadagi qo'ng'iroqcha).

Bildirishnoma saqlanmaydi — har sahifada joriy holatdan hisoblanadi, shuning uchun ish bajarilgach o'zi yo'qoladi.
Hammasi rol va filial cheklovi bilan (`hisoblar.huquqlar`); filiallar bir marta o'qiladi, har tur — bitta so'rov.
"""
from django.db.models import Count, Exists, OuterRef, Q
from django.urls import reverse

from chiqimlar.models import ChiqimHujjat
from hisoblar.huquqlar import huquqi_bor, ruxsat_filial_idlar
from mol.models import MolAkt, MolAktQator
from reviziya.models import Reviziya


def kutayotgan_ishlar(user) -> list[dict]:
    """[{nomi, soni, url, ikonka}] — faqat soni noldan katta ishlar."""
    ishlar = []
    idlar = ruxsat_filial_idlar(user)  # None — hamma filial

    def chekla(qs):
        return qs if idlar is None else qs.filter(filial__in=idlar)

    # 1C chiqimlari — ularni tasdiqlay oladiganlarga (HR va rahbar uchun vazifa emas)
    if huquqi_bor(user, "taqsimot"):
        H = ChiqimHujjat.Holat
        sonlar = chekla(ChiqimHujjat.objects.filter(holat__in=(H.KUTILMOQDA, H.BEKOR_1C))).aggregate(
            kutilmoqda=Count("pk", filter=Q(holat=H.KUTILMOQDA)), bekor=Count("pk", filter=Q(holat=H.BEKOR_1C)),
        )
        url = reverse("chiqimlar:royxat")
        ishlar.append({"nomi": "1C chiqimi tasdiq kutmoqda", "soni": sonlar["kutilmoqda"],
                       "url": f"{url}?holat={H.KUTILMOQDA}", "ikonka": "cil-swap-horizontal", "tur": "chiqim"})
        ishlar.append({"nomi": "1C'da bekor qilingan — tasdiqni qaytarish kerak", "soni": sonlar["bekor"],
                       "url": f"{url}?holat={H.BEKOR_1C}", "ikonka": "cil-warning", "tur": "chiqim"})
    # Qoralama МОЛ aktlari (masalan, reviziyada revizor Javobgar shaxsga biriktirgan AV'lar)
    if huquqi_bor(user, "mol_akt"):
        aktlar = MolAkt.objects.filter(holat=MolAkt.Holat.QORALAMA)
        if idlar is not None:  # `mol.sorovlar.korinadigan_aktlar` bilan bir xil: barcha qatorlari ruxsat etilgan filialda
            aktlar = aktlar.exclude(Exists(MolAktQator.objects.filter(akt=OuterRef("pk")).exclude(filial__in=idlar)))
        soni = aktlar.count()
        ishlar.append({"nomi": "Topshirish akti tasdiq kutmoqda", "soni": soni,
                       "url": f"{reverse('mol:akt_royxat')}?holat={MolAkt.Holat.QORALAMA}", "ikonka": "cil-description",
                       "tur": "akt"})
    # Revizor sifatida biriktirilgan ochiq reviziyalar
    if huquqi_bor(user, "reviziya_korish"):
        soni = chekla(Reviziya.objects.filter(holat=Reviziya.Holat.OCHIQ, revizorlar=user)).distinct().count()
        url = reverse("reviziya:royxat") + "?holat=ochiq" if huquqi_bor(user, "korish") else reverse("reviziya:mobil")
        ishlar.append({"nomi": "Siz revizor bo'lgan ochiq reviziya", "soni": soni, "url": url, "ikonka": "cil-task",
                       "tur": "reviziya"})
    return [i for i in ishlar if i["soni"]]
