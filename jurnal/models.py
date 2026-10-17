from django.conf import settings
from django.db import models
from django.utils import timezone


class Jurnal(models.Model):
    """O'zgarishlar jurnali: kim, qachon, qaysi obyektning qaysi maydonini o'zgartirdi."""

    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Foydalanuvchi o'chirilsa ham jurnalda nomi qoladi; 1C sinxron uchun "1C sinxron".
    kim_nomi = models.CharField(max_length=255)
    qachon = models.DateTimeField(default=timezone.now)
    obyekt_turi = models.CharField(max_length=100)  # "app_label.model"
    obyekt_id = models.CharField(max_length=64)
    maydon = models.CharField(max_length=100)
    eski = models.TextField(blank=True)
    yangi = models.TextField(blank=True)

    class Meta:
        ordering = ["-qachon", "-id"]
        indexes = [models.Index(fields=["obyekt_turi", "obyekt_id"])]

    def __str__(self):
        return f"{self.kim_nomi}: {self.obyekt_turi}#{self.obyekt_id}.{self.maydon}"
