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
