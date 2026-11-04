from django.conf import settings
from django.db import models


class OqilganIsh(models.Model):
    """Foydalanuvchi «Kutayotgan ishlar» dagi bir turni o'qigan paytdagi obyektlar (har kim — o'zi uchun).

    Ish bajarilmaguncha ro'yxatda qoladi, lekin qizil belgi faqat shu yerda yo'q yangi obyektlar uchun chiqadi.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oqilgan_ishlar")
    kalit = models.CharField(max_length=32)  # panel.vazifalar: chiqim_kutilmoqda, chiqim_bekor, akt, reviziya
    idlar = models.JSONField(default=list)
    qachon = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "O'qilgan ish"
        verbose_name_plural = "O'qilgan ishlar"
        constraints = [models.UniqueConstraint(fields=["user", "kalit"], name="oqilgan_ish_user_kalit")]

    def __str__(self):
        return f"{self.user} · {self.kalit}"
