"""Rol va filial bo'yicha huquqlar. Tekshiruv har so'rovda server tomonida."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from .models import Rol

# amal -> shu amalga ruxsati bor rollar. Revizor 1-bosqichda panelga kirmaydi.
HUQUQLAR: dict[str, set[str]] = {
    "korish": {Rol.ADMIN, Rol.HISOBCHI, Rol.HR, Rol.RAHBAR},
    "av_tahrir": {Rol.ADMIN, Rol.HISOBCHI},
    "taqsimot": {Rol.ADMIN, Rol.HISOBCHI},
    "bolim_tahrir": {Rol.ADMIN, Rol.HISOBCHI},
    "mol_akt": {Rol.ADMIN, Rol.HISOBCHI, Rol.HR},
    "yorliq": {Rol.ADMIN, Rol.HISOBCHI},
    "tozalash": {Rol.ADMIN, Rol.HISOBCHI},
    "hisobot": {Rol.ADMIN, Rol.HISOBCHI, Rol.HR, Rol.RAHBAR},
    # Summa, qiymat, dona narxi, amortizatsiya va 1C izohi: sahifa, Excel, PDF va tarixda. HR — faqat soni.
    "pul_korish": {Rol.ADMIN, Rol.HISOBCHI, Rol.RAHBAR},
    # «1C chiqimlari» sahifasi: rahbarga kerak emas (menyuda ham, bosh sahifa plitkasida ham ko'rinmaydi).
    "chiqim_korish": {Rol.ADMIN, Rol.HISOBCHI, Rol.HR},
    "sozlama": {Rol.ADMIN},
    "sinxron": {Rol.ADMIN},
}


def rol_of(user) -> str | None:
    if not getattr(user, "is_authenticated", False):
        return None
    profil = getattr(user, "profil", None)
    return profil.rol if profil else None


def huquqi_bor(user, amal: str) -> bool:
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return amal in HUQUQLAR
    return rol_of(user) in HUQUQLAR.get(amal, set())


def ruxsat_filial_idlar(user) -> set[int] | None:
    """Ruxsat berilgan filial pk'lari; None = hamma filial."""
    if user.is_superuser:
        return None
    profil = getattr(user, "profil", None)
    if profil is None:
        return set()
    idlar = set(profil.filiallar.values_list("pk", flat=True))
    return idlar or None


def filial_bilan_chekla(qs: QuerySet, user, maydon: str = "filial") -> QuerySet:
    idlar = ruxsat_filial_idlar(user)
    if idlar is None:
        return qs
    return qs.filter(**{f"{maydon}__in": idlar})


def amal_kerak(amal: str):
    """Dekorator: kirmagan -> kirish sahifasiga; huquq yo'q -> 403."""

    def dekorator(view):
        @wraps(view)
        def ichki(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not huquqi_bor(request.user, amal):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return ichki

    return dekorator
