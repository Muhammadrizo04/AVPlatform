from django.conf import settings
from django.db import models


class Rol(models.TextChoices):
    ADMIN = "admin", "Administrator"
    HISOBCHI = "hisobchi", "Hisobchi"
    HR = "hr", "HR"
    RAHBAR = "rahbar", "Rahbar"
    REVIZOR = "revizor", "Revizor"


class Profil(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profil")
    # Eng kam huquq standart: rol aniq berilmaguncha panelga kirib bo'lmaydi.
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.REVIZOR)
    # Bo'sh = hamma filial
    filiallar = models.ManyToManyField("onec.Filial", blank=True, related_name="profillar")

    def __str__(self):
        return f"{self.user} ({self.get_rol_display()})"
