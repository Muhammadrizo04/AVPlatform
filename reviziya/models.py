from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from vositalar.models import Holat as TaqsimotHolat

User = settings.AUTH_USER_MODEL


class Reviziya(models.Model):
    """Inventarizatsiya (reviziya) hujjati: ochiq -> yakunlangan -> yopilgan («qollangan») yoki bekor."""

    class Holat(models.TextChoices):
        OCHIQ = "ochiq", "Ochiq"
        YAKUNLANGAN = "yakunlangan", "Yakunlangan"
        QOLLANGAN = "qollangan", "Yopilgan"  # qiymat o'zgarmaydi (bazadagi yozuvlar)
        BEKOR = "bekor", "Bekor qilingan"

    raqam = models.PositiveIntegerField(unique=True)
    filial = models.ForeignKey("onec.Filial", on_delete=models.PROTECT, related_name="+")
    bolim = models.ForeignKey("vositalar.Bolim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    holat = models.CharField(max_length=20, choices=Holat.choices, default=Holat.OCHIQ)
    revizorlar = models.ManyToManyField(User, blank=True, related_name="reviziyalar")
    komissiya = models.JSONField(default=list, blank=True)
    izoh = models.TextField(blank=True)
    ochdi = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    ochilgan_vaqt = models.DateTimeField(default=timezone.now)
    yakunladi = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    yakunlangan_vaqt = models.DateTimeField(null=True, blank=True)
    qolladi = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    qollangan_vaqt = models.DateTimeField(null=True, blank=True)
    bekor_qildi = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    bekor_vaqti = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nomi

    @property
    def nomi(self) -> str:
        return f"RV-{self.raqam:06d}"


class ReviziyaKutilgan(models.Model):
    """Reviziya ochilgan paytdagi kutilgan (taqsimot) holati."""

    reviziya = models.ForeignKey(Reviziya, on_delete=models.CASCADE, related_name="kutilganlar")
    av = models.ForeignKey("onec.AV", on_delete=models.PROTECT, related_name="+")
    bolim = models.ForeignKey("vositalar.Bolim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    mol = models.ForeignKey("onec.Xodim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    holat = models.CharField(max_length=30, choices=TaqsimotHolat.choices)
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    taqsimot_id = models.IntegerField()


class ReviziyaQayd(models.Model):
    """Revizor qaydi: sanalgan AV (yoki noma'lum QR matni)."""

    class Usul(models.TextChoices):
        QR = "qr", "QR"
        QIDIRUV = "qidiruv", "Qidiruv"

    reviziya = models.ForeignKey(Reviziya, on_delete=models.CASCADE, related_name="qaydlar")
    bolim = models.ForeignKey("vositalar.Bolim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    av = models.ForeignKey("onec.AV", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    qr_matn = models.CharField(max_length=255, blank=True)
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    holat = models.CharField(max_length=30, choices=TaqsimotHolat.choices)
    izoh = models.TextField(blank=True)
    rasm = models.ForeignKey("vositalar.Rasm", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    usul = models.CharField(max_length=10, choices=Usul.choices)
    kim = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    qachon = models.DateTimeField(default=timezone.now)
    yangilangan = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reviziya", "bolim", "av", "holat", "qr_matn"],
                nulls_distinct=False,
                name="reviziya_qayd_noyob",
            )
        ]


class ReviziyaXona(models.Model):
    """Bo'lim (xona) sanab bo'lindi belgisi — yozuv bor bo'lsa xona tugagan. Skanerlashni to'xtatmaydi."""

    reviziya = models.ForeignKey(Reviziya, on_delete=models.CASCADE, related_name="tugagan_xonalar")
    bolim = models.ForeignKey("vositalar.Bolim", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    tugatdi = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    tugagan_vaqt = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reviziya", "bolim"], nulls_distinct=False, name="reviziya_xona_noyob")
        ]


class ReviziyaQollash(models.Model):
    """Qo'llash jurnali: har guruh (kalit) uchun natija; muvaffaqiyatli kalit takrorlanmaydi (bekor qilinmaguncha)."""

    class Natija(models.TextChoices):
        OK = "ok", "OK"
        XATO = "xato", "Xato"
        BEKOR = "bekor", "Bekor qilingan"

    reviziya = models.ForeignKey(Reviziya, on_delete=models.CASCADE, related_name="qollashlar")
    kalit = models.CharField(max_length=255)
    guruh = models.CharField(max_length=255)
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    natija = models.CharField(max_length=10, choices=Natija.choices)
    xato = models.TextField(blank=True)
    kim = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    qachon = models.DateTimeField(default=timezone.now)
    # natija="bekor": qo'llash teskari amal bilan bekor qilingan — kalitni yana qo'llash mumkin
    bekor_qildi = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    bekor_vaqti = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reviziya", "kalit"],
                condition=Q(natija="ok"),
                name="reviziya_qollash_ok_noyob",
            )
        ]


class XodimLavozimi(models.Model):
    """Komissiyada yozilgan lavozim (1C'da lavozim yo'q) — keyingi reviziyada a'zo tanlanganda o'zi to'ladi."""

    xodim = models.OneToOneField("onec.Xodim", on_delete=models.CASCADE, primary_key=True, related_name="+")
    lavozim = models.CharField(max_length=255)

    def __str__(self):
        return self.lavozim
