"""`panel.saralash.Saralash` va `{% saralash_ustuni %}` / `{% sahifa_url %}` teglari."""
from types import SimpleNamespace

import pytest
from django.template import Context, Template
from django.test import RequestFactory

from onec.models import Filial
from panel.saralash import Saralash

USTUNLAR = {"nomi": lambda e: e.nomi, "soni": lambda e: e.soni}


def _so_rov(**params):
    return RequestFactory().get("/", params)


def _e(nomi, soni):
    return SimpleNamespace(nomi=nomi, soni=soni)


def test_royxat_osuvchi_kamayuvchi_va_none_oxirida():
    elementlar = [_e("b", 2), _e("a", None), _e("c", 1)]
    assert [e.nomi for e in Saralash(_so_rov(tartib="soni"), USTUNLAR).royxat(elementlar)] == ["c", "b", "a"]
    assert [e.nomi for e in Saralash(_so_rov(tartib="-soni"), USTUNLAR).royxat(elementlar)] == ["b", "c", "a"]


def test_nomalum_kalit_standartga_qaytadi():
    s = Saralash(_so_rov(tartib="-parol"), USTUNLAR, standart="-soni")
    assert (s.kalit, s.teskari) == ("soni", True)
    s = Saralash(_so_rov(tartib="parol"), USTUNLAR)
    assert not s.tanlangan
    assert [e.nomi for e in s.royxat([_e("b", 1), _e("a", 2)])] == ["b", "a"]  # tartib o'zgarmaydi


@pytest.mark.django_db
def test_queryset_kamayuvchi(filial_yarat):
    a, b = filial_yarat("01"), filial_yarat("02")
    qs = Saralash(_so_rov(tartib="-kod"), {"kod": "kod"}).queryset(Filial.objects.filter(pk__in=[a.pk, b.pk]))
    assert list(qs) == [b, a]


def _chiz(shablon, request, saralash):
    return Template("{% load jadval %}" + shablon).render(Context({"request": request, "saralash": saralash}))


def test_sarlavha_havolasi_parametrlarni_saqlaydi_sahifani_tashlaydi():
    so_rov = _so_rov(q="stol", page="3", tartib="nomi")
    html = _chiz('{% saralash_ustuni "nomi" "Nomi" %}{% saralash_ustuni "soni" "Soni" "son" %}', so_rov,
                 Saralash(so_rov, USTUNLAR))
    assert 'aria-sort="ascending"' in html and "q=stol" in html and "tartib=-nomi" in html and "page=" not in html
    assert '<th class="son" aria-sort="none">' in html and "tartib=soni" in html
    # ro'yxatda yo'q ustun — oddiy sarlavha
    assert _chiz('{% saralash_ustuni "summa" "Summa" %}', so_rov, Saralash(so_rov, USTUNLAR)) == '<th class="">Summa</th>'


def test_sahifa_url_va_tartib_maydoni():
    so_rov = _so_rov(q="stol", tartib="-soni", page="1")
    s = Saralash(so_rov, USTUNLAR)
    html = _chiz("{% sahifa_url 4 %}|{% tartib_maydoni %}", so_rov, s)
    url, maydon = html.split("|")
    assert "page=4" in url and "tartib=-soni" in url and "q=stol" in url
    assert maydon == '<input type="hidden" name="tartib" value="-soni">'
