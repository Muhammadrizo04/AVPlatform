"""Reviziyani kim o'zgartira oladi (yakunlash, bekor qilish, ochiqqa qaytarish, revizorlar, qayd va belgilar).

Standart: `reviziya_boshqarish` huquqi borlar (filial cheklovi ichida) va shu reviziya revizorlari.
«Faqat o'z reviziyasi» sozlamasi (`Sozlama.reviziya_faqat_ozimniki`) yoqilsa: faqat admin, reviziyani ochgan
kishi va unga biriktirilgan revizorlar; boshqalar reviziyani faqat ko'radi.
"""
from django.db.models import Q

from hisoblar.huquqlar import huquqi_bor, rol_of
from hisoblar.models import Rol
from vositalar.models import Sozlama


def _admin(user) -> bool:
    return user.is_superuser or rol_of(user) == Rol.ADMIN


def ozgartiradigan_shart(user) -> Q:
    """Foydalanuvchi o'zgartira oladigan reviziyalar sharti (`Reviziya` querysetiga; `.distinct()` bilan)."""
    if _admin(user):
        return Q()
    if Sozlama.ol().reviziya_faqat_ozimniki:
        return Q(ochdi=user) | Q(revizorlar=user)
    if huquqi_bor(user, "reviziya_boshqarish"):
        return Q()
    return Q(revizorlar=user)


def ozgartira_oladi(user, rv) -> bool:
    """`rv` ni o'zgartira oladimi (filial cheklovi chaqiruvchida tekshirilgan)."""
    if _admin(user):
        return True
    revizori = rv.revizorlar.filter(pk=user.pk).exists()
    if Sozlama.ol().reviziya_faqat_ozimniki:
        return rv.ochdi_id == user.pk or revizori
    return huquqi_bor(user, "reviziya_boshqarish") or revizori
