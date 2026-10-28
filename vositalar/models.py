from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Holat(models.TextChoices):
    ISHLATILMOQDA = "ishlatilmoqda", "Ishlatilmoqda"
    ZAXIRADA = "zaxirada", "Zaxirada"
    TAMIRDA = "tamirda", "Ta'mirda"
    NOSOZ = "nosoz", "Nosoz"
    HISOBDAN_CHIQARISHGA = "hisobdan_chiqarishga", "Hisobdan chiqarishga"
    TOPILMADI = "topilmadi", "Topilmadi"


class Bolim(models.Model):
    """Filial ichidagi bo'lim; `ota` orqali daraxt (bo'lim -> xona/joy)."""

    filial = models.ForeignKey("onec.Filial", on_delete=models.PROTECT, related_name="bolimlar")
    ota = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="bolalar")
    nomi = models.CharField(max_length=255)
    faol = models.BooleanField(default=True)

    def __str__(self):
        return self.toliq_nomi

    @property
    def toliq_nomi(self) -> str:
        """Ildizdan boshlab yo'l: "Savdo zali / Kassa 2"."""
        qismlar = []
        bolim, korilgan = self, set()
        while bolim is not None and bolim.pk not in korilgan:
            korilgan.add(bolim.pk)
            qismlar.append(bolim.nomi)
            bolim = bolim.ota
        return " / ".join(reversed(qismlar))


class AVTuriSozlama(models.Model):
    """AV turi bo'yicha standart xizmat muddati va qo'shimcha maydonlar ro'yxati.

    `maydonlar` elementi: {kalit, nomi, tip: matn|son|sana|tanlov, tanlov_qiymatlari: [..], majburiy: bool}.
    """

    av_turi = models.OneToOneField("onec.AVTuri", on_delete=models.PROTECT, related_name="sozlama")
    xizmat_muddati_oy = models.PositiveIntegerField(null=True, blank=True)
    maydonlar = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.av_turi} sozlamasi"


class AVKartochka(models.Model):
    """AV'ning platformadagi qo'shimcha kartochkasi (butun guruh uchun umumiy)."""

    av = models.OneToOneField("onec.AV", on_delete=models.PROTECT, related_name="kartochka")
    ishga_tushgan_sana = models.DateField(null=True, blank=True)
    xizmat_muddati_oy = models.PositiveIntegerField(null=True, blank=True)
    qoshimcha = models.JSONField(default=dict, blank=True)
    izoh = models.TextField(blank=True)
    yorliq_kaliti = models.CharField(max_length=255, null=True, blank=True)
    yorliq_sana = models.DateTimeField(null=True, blank=True)
    versiya = models.PositiveIntegerField(default=1)  # optimistik blokirovka uchun

    def __str__(self):
        return f"{self.av} kartochkasi"


class Rasm(models.Model):
    av = models.ForeignKey("onec.AV", on_delete=models.PROTECT, related_name="rasmlar")
    fayl = models.FileField(upload_to="rasmlar/")
    miniatyura = models.FileField(upload_to="rasmlar/mini/", blank=True)
    asosiy = models.BooleanField(default=False)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    qachon = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-asosiy", "-qachon"]


class Taqsimot(models.Model):
    """AV'ning filial ichidagi taqsimoti: bo'lim, MOL va holat bo'yicha.

    Invariant: har (av, filial) uchun Σ soni = AVQoldiq.soni.
    """

    av = models.ForeignKey("onec.AV", on_delete=models.PROTECT, related_name="taqsimotlar")
    filial = models.ForeignKey("onec.Filial", on_delete=models.PROTECT, related_name="taqsimotlar")
    bolim = models.ForeignKey(Bolim, null=True, blank=True, on_delete=models.PROTECT, related_name="taqsimotlar")
    mol = models.ForeignKey(
        "onec.Xodim", null=True, blank=True, on_delete=models.PROTECT, related_name="taqsimotlar"
    )
    holat = models.CharField(max_length=30, choices=Holat.choices, default=Holat.ISHLATILMOQDA)
    soni = models.DecimalField(max_digits=15, decimal_places=3)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(soni__gt=0), name="taqsimot_soni_musbat"),
            # Bo'sh bo'lim/MOL ham bir xil deb hisoblanadi: bir xil qatorlar birlashadi.
            models.UniqueConstraint(
                fields=["av", "filial", "bolim", "mol", "holat"], nulls_distinct=False, name="taqsimot_unikal"
            ),
        ]


class TaqsimotHarakat(models.Model):
    """Taqsimotdagi har bir o'zgarish. `eski_*` bo'sh — son 1C'dan kelgan."""

    class Sabab(models.TextChoices):
        KOCHIRISH = "kochirish", "Ko'chirish"
        HOLAT = "holat", "Holat o'zgarishi"
        MOL_AKT = "mol_akt", "Topshirish akti"
        ONEC_KOPAYDI = "1c_kopaydi", "1C'da ko'paydi"
        ONEC_KAMAYDI = "1c_kamaydi", "1C'da kamaydi"
        ONEC_NOLGA_TUSHDI = "1c_nolga_tushdi", "1C'da nolga tushdi"
        SOTILDI = "sotildi", "Sotildi"
        OTKAZILDI = "otkazildi", "Filialga o'tkazildi"
        HISOBDAN_CHIQARILDI = "hisobdan_chiqarildi", "Hisobdan chiqarildi"
        REVIZIYA = "reviziya", "Reviziya"
        CHIQIM_QAYTARILDI = "chiqim_qaytarildi", "1C chiqimi qaytarildi"

    av = models.ForeignKey("onec.AV", on_delete=models.PROTECT, related_name="taqsimot_harakatlari")
    filial = models.ForeignKey("onec.Filial", on_delete=models.PROTECT, related_name="+")
    eski_bolim = models.ForeignKey(Bolim, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    eski_mol = models.ForeignKey("onec.Xodim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    eski_holat = models.CharField(max_length=30, choices=Holat.choices, blank=True)
    yangi_bolim = models.ForeignKey(Bolim, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    yangi_mol = models.ForeignKey("onec.Xodim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    yangi_holat = models.CharField(max_length=30, choices=Holat.choices, blank=True)
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    sana = models.DateTimeField(default=timezone.now)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    sabab = models.CharField(max_length=20, choices=Sabab.choices)
    hujjat_izoh = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-sana", "-id"]


class Sozlama(models.Model):
    """Platforma sozlamalari — yagona yozuv (`Sozlama.ol()`)."""

    PK = 1

    kompaniya_nomi = models.CharField(max_length=255, blank=True)
    chiqim_boshlanishi = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.kompaniya_nomi or "Sozlama"

    @classmethod
    def ol(cls) -> "Sozlama":
        obyekt, _ = cls.objects.get_or_create(pk=cls.PK)
        return obyekt


class YorliqOlchami(models.Model):
    """Yorliq (QR) chop etish o'lchami, mm."""

    nomi = models.CharField(max_length=50)
    eni_mm = models.DecimalField(max_digits=5, decimal_places=1)
    boyi_mm = models.DecimalField(max_digits=5, decimal_places=1)
    faol = models.BooleanField(default=True)
    standart = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(eni_mm__gte=20, eni_mm__lte=120), name="yorliq_eni_oraliq"),
            models.CheckConstraint(condition=Q(boyi_mm__gte=15, boyi_mm__lte=120), name="yorliq_boyi_oraliq"),
            # Faqat bitta standart o'lcham bo'lishi mumkin.
            models.UniqueConstraint(fields=["standart"], condition=Q(standart=True), name="yorliq_bitta_standart"),
        ]

    def __str__(self):
        return self.nomi

    @classmethod
    def standarti(cls) -> "YorliqOlchami":
        """Faol standart o'lcham; yo'q bo'lsa — birinchi faol o'lcham; faol o'lcham umuman yo'q bo'lsa DoesNotExist."""
        olcham = cls.objects.filter(faol=True).order_by("-standart", "eni_mm", "boyi_mm", "pk").first()
        if olcham is None:
            raise cls.DoesNotExist("Faol yorliq o'lchami yo'q. Sozlamalarda o'lcham qo'shing yoki faollashtiring.")
        return olcham
