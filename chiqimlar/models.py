from django.conf import settings
from django.db import models


class ChiqimHujjat(models.Model):
    """1C'dagi chiqim harakati: hisobchi turini tasdiqlamaguncha taqsimot o'zgarmaydi."""

    class Holat(models.TextChoices):
        KUTILMOQDA = "kutilmoqda", "Kutilmoqda"
        TASDIQLANGAN = "tasdiqlangan", "Tasdiqlangan"
        # tasdiqlangandan keyin 1C'da hujjat bekor qilindi — taqsimotni qaytarish kerak («Tasdiqni qaytarish»)
        BEKOR_1C = "bekor_1c", "1C'da bekor qilindi"
        BEKOR = "bekor", "Bekor qilingan"

    class Tur(models.TextChoices):
        OTKAZISH = "otkazish", "Filialga o'tkazish"
        SOTILDI = "sotildi", "Sotildi"
        HISOBDAN_CHIQARILDI = "hisobdan_chiqarildi", "Hisobdan chiqarildi"

    hujjat_turi = models.CharField(max_length=100)
    hujjat_raqami = models.CharField(max_length=50)
    hujjat_ref = models.UUIDField()
    sana = models.DateTimeField()
    av = models.ForeignKey("onec.AV", on_delete=models.PROTECT, related_name="chiqimlar")
    filial = models.ForeignKey("onec.Filial", on_delete=models.PROTECT, related_name="chiqimlar")
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    summa = models.DecimalField(max_digits=15, decimal_places=2)
    holat = models.CharField(max_length=20, choices=Holat.choices, default=Holat.KUTILMOQDA)
    taxmin_tur = models.CharField(max_length=20, choices=Tur.choices)
    tur = models.CharField(max_length=20, choices=Tur.choices, blank=True)
    qabul_filial = models.ForeignKey(
        "onec.Filial", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    izoh = models.TextField(blank=True)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    qachon = models.DateTimeField(null=True, blank=True)
    # tasdiqlashda qaysi taqsimot qatorlaridan qancha ayirilgani: [{"bolim", "mol", "holat", "soni"}] — qaytarish uchun
    ayirilganlar = models.JSONField(default=list, blank=True)
    yaratildi = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sana", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["hujjat_ref", "av", "filial"], name="chiqim_unikal"),
        ]
        indexes = [models.Index(fields=["holat", "filial"], name="chiqim_holat_filial_idx")]

    def __str__(self):
        return f"{self.hujjat_turi} {self.hujjat_raqami}"
