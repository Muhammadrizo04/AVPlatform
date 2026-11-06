"""«Kutayotgan ishlar»: foydalanuvchi bajarishi kerak bo'lgan ishlar soni (tepadagi qo'ng'iroqcha).

Ishlarning o'zi saqlanmaydi — har sahifada joriy holatdan hisoblanadi, shuning uchun ish bajarilgach o'zi yo'qoladi.
«O'qildi» esa har foydalanuvchi uchun alohida (`OqilganIsh`): o'qilgan paytdagi obyektlar eslab qolinadi va qizil
belgi faqat ulardan keyin paydo bo'lgan yangi obyektlar uchun chiqadi. Bir kishi o'qisa — boshqalarda o'zgarmaydi.
Hammasi rol va filial cheklovi bilan (`hisoblar.huquqlar`); filiallar bir marta o'qiladi, har tur — bitta so'rov.
"""
from django.db.models import Exists, OuterRef
from django.urls import reverse

from chiqimlar.models import ChiqimHujjat
from hisoblar.huquqlar import huquqi_bor, ruxsat_filial_idlar
from mol.models import MolAkt, MolAktQator
from reviziya.models import Reviziya

from .models import OqilganIsh


def _ishlar(user) -> list[dict]:
    """[{kalit, nomi, soni, idlar, url, ikonka, tur}] — faqat soni noldan katta ishlar, o'qilganlik hisobisiz."""
    ishlar = []
    idlar = ruxsat_filial_idlar(user)  # None — hamma filial

    def chekla(qs):
        return qs if idlar is None else qs.filter(filial__in=idlar)

    def ish(kalit, nomi, qs, url, ikonka, tur):
        pklar = sorted(qs.values_list("pk", flat=True))
        ishlar.append({"kalit": kalit, "nomi": nomi, "soni": len(pklar), "idlar": pklar, "url": url,
                       "ikonka": ikonka, "tur": tur})

    # 1C chiqimlari — ularni tasdiqlay oladiganlarga (HR va rahbar uchun vazifa emas)
    if huquqi_bor(user, "taqsimot"):
        H = ChiqimHujjat.Holat
        url = reverse("chiqimlar:royxat")
        ish("chiqim_kutilmoqda", "1C chiqimi tasdiq kutmoqda", chekla(ChiqimHujjat.objects.filter(holat=H.KUTILMOQDA)),
            f"{url}?holat={H.KUTILMOQDA}", "cil-swap-horizontal", "chiqim")
        ish("chiqim_bekor", "1C'da bekor qilingan — tasdiqni qaytarish kerak",
            chekla(ChiqimHujjat.objects.filter(holat=H.BEKOR_1C)), f"{url}?holat={H.BEKOR_1C}", "cil-warning", "chiqim")
        ish("chiqim_ozgargan", "1C'da chiqim soni o'zgargan — tasdiqni yangilash kerak",
            chekla(ChiqimHujjat.objects.filter(holat=H.TASDIQLANGAN, ozgargan_soni__isnull=False)),
            f"{url}?holat={H.TASDIQLANGAN}&ozgargan=1", "cil-warning", "chiqim")
    # Qoralama МОЛ aktlari (masalan, reviziyada revizor Javobgar shaxsga biriktirgan AV'lar)
    if huquqi_bor(user, "mol_akt"):
        aktlar = MolAkt.objects.filter(holat=MolAkt.Holat.QORALAMA)
        if idlar is not None:  # `mol.sorovlar.korinadigan_aktlar` bilan bir xil: barcha qatorlari ruxsat etilgan filialda
            aktlar = aktlar.exclude(Exists(MolAktQator.objects.filter(akt=OuterRef("pk")).exclude(filial__in=idlar)))
        ish("akt", "Topshirish akti tasdiq kutmoqda", aktlar,
            f"{reverse('mol:akt_royxat')}?holat={MolAkt.Holat.QORALAMA}", "cil-description", "akt")
    # Revizor sifatida biriktirilgan ochiq reviziyalar
    if huquqi_bor(user, "reviziya_korish"):
        url = reverse("reviziya:royxat") + "?holat=ochiq" if huquqi_bor(user, "korish") else reverse("reviziya:mobil")
        ish("reviziya", "Siz revizor bo'lgan ochiq reviziya",
            chekla(Reviziya.objects.filter(holat=Reviziya.Holat.OCHIQ, revizorlar=user)).distinct(), url, "cil-task",
            "reviziya")
    return [i for i in ishlar if i["soni"]]


def kutayotgan_ishlar(user) -> list[dict]:
    """`_ishlar` + har biriga `yangi` — foydalanuvchi hali o'qimagan obyektlar soni (qizil belgi shundan)."""
    ishlar = _ishlar(user)
    if ishlar:
        oqilgan = dict(OqilganIsh.objects.filter(user=user).values_list("kalit", "idlar"))
        for i in ishlar:
            i["yangi"] = len(set(i["idlar"]) - set(oqilgan.get(i["kalit"], ())))
    return ishlar


def oqildi_belgila(user, kalit: str | None = None) -> None:
    """Bitta turni (`kalit`) yoki hammasini joriy holat bo'yicha o'qilgan qiladi — faqat shu foydalanuvchi uchun."""
    for i in _ishlar(user):
        if kalit is None or i["kalit"] == kalit:
            OqilganIsh.objects.update_or_create(user=user, kalit=i["kalit"], defaults={"idlar": i["idlar"]})
