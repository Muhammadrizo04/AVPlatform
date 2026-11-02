"""Ruxsat etilgan filiallar ro'yxati bir so'rovda qayta-qayta bazadan o'qilmasligi kerak."""
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from hisoblar.huquqlar import ruxsat_filial_idlar


def _filial_sorovlari(q):
    return [x for x in q.captured_queries if "hisoblar_profil_filiallar" in x["sql"]]


def test_ruxsat_filial_idlar_kesh(filial_yarat, foydalanuvchi):
    f = filial_yarat("A")
    user = foydalanuvchi("hisobchi", [f])
    with CaptureQueriesContext(connection) as q:
        for _ in range(5):
            assert ruxsat_filial_idlar(user) == {f.pk}
    assert len(_filial_sorovlari(q)) == 1


def test_av_royxati_filial_sorovlari_kam(filial_yarat, foydalanuvchi):
    f = filial_yarat("A")
    c = Client()
    c.force_login(foydalanuvchi("hisobchi", [f]))
    with CaptureQueriesContext(connection) as q:
        assert c.get(reverse("vositalar:royxat")).status_code == 200
    assert len(_filial_sorovlari(q)) <= 2  # oldin 16
