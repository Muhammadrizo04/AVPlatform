import itertools
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

PAROL = "sinov-parol-12345"

_hisoblagich = itertools.count(1)


@pytest.fixture
def foydalanuvchi(db):
    """Fabrika: foydalanuvchi(rol, filiallar=()) -> Profil'li User."""
    from hisoblar.models import Profil

    def yarat(rol, filiallar=()):
        user = get_user_model().objects.create_user(
            username=f"{rol}_{next(_hisoblagich)}", password=PAROL
        )
        profil = Profil.objects.create(user=user, rol=rol)
        profil.filiallar.set(filiallar)
        return user

    return yarat


@pytest.fixture
def client_rol(foydalanuvchi):
    """Fabrika: client_rol(rol) -> shu rolda tizimga kirgan test Client."""

    def yarat(rol):
        client = Client()
        client.force_login(foydalanuvchi(rol))
        return client

    return yarat


@pytest.fixture
def filial_yarat(db):
    """Fabrika: filial_yarat(kod, nomi=None) -> onec.Filial."""
    from onec.models import Filial

    def yarat(kod, nomi=None):
        return Filial.objects.create(ref_1c=uuid.uuid4(), kod=kod, nomi=nomi or f"Filial {kod}")

    return yarat


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Migratsiyalar yozadigan boshlang'ich ma'lumotlar (`--reuse-db` da ham) har sessiya boshida tiklanadi:
    `transaction=True` testlari (parallel so'rovlar) bazani tozalab, ularni ham o'chiradi."""
    import importlib

    from django.apps import apps

    with django_db_blocker.unblock():
        importlib.import_module("vositalar.migrations.0002_boshlangich_yorliq_olchamlari").olchamlar_yarat(apps, None)
        importlib.import_module("vositalar.migrations.0003_chiqim").chiqim_boshlanishini_yoz(apps, None)
