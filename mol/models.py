from django.conf import settings
from django.db import models
from django.utils import timezone

from vositalar.models import Holat as TaqsimotHolat


class MolAkt(models.Model):
    """МОЛ topshirish-qabul akti: qoralama -> tasdiqlangan yoki bekor (spec §7.6, §8)."""

    class Holat(models.TextChoices):
        QORALAMA = "qoralama", "Qoralama"
        TASDIQLANGAN = "tasdiqlangan", "Tasdiqlangan"
        BEKOR = "bekor", "Bekor qilingan"

    raqam = models.PositiveIntegerField(unique=True)
    sana = models.DateField(default=timezone.localdate)
    # Bo'sh topshiruvchi — birinchi biriktirish (МОЛ'siz qatordan).
    topshiruvchi = models.ForeignKey(
        "onec.Xodim", null=True, blank=True, on_delete=models.PROTECT, related_name="topshirgan_aktlar"
    )
    qabul_qiluvchi = models.ForeignKey("onec.Xodim", on_delete=models.PROTECT, related_name="qabul_qilgan_aktlar")
    izoh = models.TextField(blank=True)
    holat = models.CharField(max_length=20, choices=Holat.choices, default=Holat.QORALAMA)
    tuzdi = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    tasdiqladi = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    tasdiq_vaqti = models.DateTimeField(null=True, blank=True)
    # Bekor qilingan qoralama o'chirilmaydi: raqami band qoladi, kim/qachon bekor qilgani saqlanadi.
    bekor_qildi = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    bekor_vaqti = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nomi

    @property
    def nomi(self) -> str:
        return f"MA-{self.raqam:06d}"


class MolAktQator(models.Model):
    """Akt qatori: (av, filial, bolim, holat) bo'yicha topshiruvchidagi `soni` dona."""

    akt = models.ForeignKey(MolAkt, on_delete=models.CASCADE, related_name="qatorlar")
    av = models.ForeignKey("onec.AV", on_delete=models.PROTECT, related_name="+")
    filial = models.ForeignKey("onec.Filial", on_delete=models.PROTECT, related_name="+")
    bolim = models.ForeignKey("vositalar.Bolim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    holat = models.CharField(max_length=30, choices=TaqsimotHolat.choices)
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    # Tasdiqlash paytidagi bir dona narxi (1C summa / soni, tiyingacha). Tasdiqlangan akt qiymati shundan olinadi
    # (keyingi 1C o'zgarishlari aktni o'zgartirmaydi); qoralamada — bo'sh, qiymat joriy 1C ma'lumotidan.
    dona_narxi = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
