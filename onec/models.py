from django.db import models


class OneCModel(models.Model):
    """1C ma'lumotining faqat o'qiladigan nusxasi uchun umumiy asos."""

    ref_1c = models.UUIDField(unique=True)
    sinx_vaqti = models.DateTimeField(null=True)
    onec_da_yoq = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Filial(OneCModel):
    kod = models.CharField(max_length=50)
    nomi = models.CharField(max_length=255)

    def __str__(self):
        return self.nomi


class Tashkilot(OneCModel):
    nomi = models.CharField(max_length=255)

    def __str__(self):
        return self.nomi


class AVTuri(OneCModel):
    """Asosiy vositalar guruhi (1C: ГруппаОС)."""

    nomi = models.CharField(max_length=255)
    tip = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nomi


class Xodim(OneCModel):
    ism = models.CharField(max_length=255)
    filial = models.ForeignKey(Filial, null=True, blank=True, on_delete=models.PROTECT)
    telefon = models.CharField(max_length=50, blank=True)
    ishdan_bushagan = models.BooleanField(default=False)
    neaktiv = models.BooleanField(default=False)
    ochirilgan = models.BooleanField(default=False)

    def __str__(self):
        return self.ism


class AV(OneCModel):
    """Asosiy vosita kartochkasi. `filial_rekvizit` — 1C rekviziti, haqiqiy joylashuv `AVQoldiq` da."""

    kod = models.CharField(max_length=50)
    nomi = models.CharField(max_length=255)
    toliq_nomi = models.CharField(max_length=500, blank=True)
    inv_raqam = models.CharField(max_length=100, blank=True)
    chiqarilgan_sana = models.DateField(null=True, blank=True)
    turi = models.ForeignKey(AVTuri, null=True, blank=True, on_delete=models.PROTECT)
    tashkilot = models.ForeignKey(Tashkilot, null=True, blank=True, on_delete=models.PROTECT)
    filial_rekvizit = models.ForeignKey(
        Filial, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    izoh_1c = models.TextField(blank=True)
    ochirilgan = models.BooleanField(default=False)

    def __str__(self):
        return self.nomi


class AVQoldiq(models.Model):
    """Filial bo'yicha AV qoldig'i (1C: УчетОС qoldiqlari)."""

    av = models.ForeignKey(AV, on_delete=models.PROTECT, related_name="qoldiqlar")
    tashkilot = models.ForeignKey(Tashkilot, null=True, blank=True, on_delete=models.PROTECT)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="qoldiqlar")
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    summa = models.DecimalField(max_digits=15, decimal_places=2)


class Harakat1C(models.Model):
    """1C'dagi AV harakati (kirim/chiqim) — faqat o'qiladigan nusxa."""

    class Vid(models.TextChoices):
        KIRIM = "kirim", "Kirim"
        CHIQIM = "chiqim", "Chiqim"

    sana = models.DateTimeField()
    hujjat_turi = models.CharField(max_length=100)
    hujjat_raqami = models.CharField(max_length=50, blank=True)
    hujjat_ref = models.UUIDField()
    av = models.ForeignKey(AV, on_delete=models.PROTECT, related_name="harakatlar")
    tashkilot = models.ForeignKey(Tashkilot, null=True, blank=True, on_delete=models.PROTECT)
    filial = models.ForeignKey(Filial, null=True, blank=True, on_delete=models.PROTECT)
    vid = models.CharField(max_length=10, choices=Vid.choices)
    soni = models.DecimalField(max_digits=15, decimal_places=3)
    summa = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["hujjat_ref"]), models.Index(fields=["sana"])]


class SinxronJurnal(models.Model):
    """Har sinxron urinishi natijasi jurnali."""

    class Natija(models.TextChoices):
        OK = "ok", "Muvaffaqiyatli"
        XATO = "xato", "Xato"
        BAND = "band", "Band (boshqa sinxron ishlayapti)"

    boshlandi = models.DateTimeField()
    tugadi = models.DateTimeField(null=True, blank=True)
    natija = models.CharField(max_length=10, choices=Natija.choices)
    xato_matni = models.TextField(blank=True)
    ozgarishlar = models.JSONField(default=dict, blank=True)
    toliq = models.BooleanField(default=False)

    class Meta:
        ordering = ["-boshlandi"]
