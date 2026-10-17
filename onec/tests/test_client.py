import base64
import json
from datetime import datetime
from pathlib import Path

import pytest
import requests
import responses
from django.test import override_settings

from onec.client import OneCClient, OneCXato

NAMUNALAR = Path(__file__).parent / "namunalar"
BAZA = "http://1c.sinov/ksb/hs/av"
LOGIN = "sinov-login"
PAROL = "sinov-parol-98765"


def namuna(nom):
    return json.loads((NAMUNALAR / f"{nom}.json").read_text(encoding="utf-8"))


@pytest.fixture
def mijoz():
    return OneCClient(BAZA, LOGIN, PAROL)


@responses.activate
def test_vositalar_namunani_qaytaradi(mijoz):
    kutilgan = namuna("vositalar")
    responses.get(f"{BAZA}/vositalar", json=kutilgan)

    natija = mijoz.vositalar()

    assert len(natija["vositalar"]) == len(kutilgan["vositalar"])
    assert natija["vositalar"][0]["ref"] == kutilgan["vositalar"][0]["ref"]
    assert len(natija["qoldiqlar"]) == len(kutilgan["qoldiqlar"])


@responses.activate
def test_spravochniklar_namunani_qaytaradi(mijoz):
    kutilgan = namuna("spravochniklar")
    responses.get(f"{BAZA}/spravochniklar", json=kutilgan)

    assert mijoz.spravochniklar() == kutilgan


@responses.activate
def test_versiya_qaytaradi(mijoz):
    responses.get(f"{BAZA}/versiya", json={"versiya": "1.0.0", "baza": "KSB"})

    assert mijoz.versiya()["versiya"] == "1.0.0"


@responses.activate
def test_harakatlar_royxatni_ochadi(mijoz):
    kutilgan = namuna("harakatlar")
    responses.get(f"{BAZA}/harakatlar", json=kutilgan)

    natija = mijoz.harakatlar(datetime(2026, 9, 1), datetime(2026, 10, 15))

    assert isinstance(natija, list)
    assert natija == kutilgan["harakatlar"]


@responses.activate
def test_harakatlar_parametr_formati(mijoz):
    responses.get(f"{BAZA}/harakatlar", json={"harakatlar": []})

    mijoz.harakatlar(datetime(2026, 9, 1), datetime(2026, 10, 15, 23, 59, 58))

    url = responses.calls[0].request.url
    assert "dan=20260901000000" in url
    assert "gacha=20261015235958" in url


@responses.activate
def test_http_500_onecxato(mijoz):
    responses.get(f"{BAZA}/vositalar", status=500, json={"xato": "ichki xato"})

    with pytest.raises(OneCXato, match="500"):
        mijoz.vositalar()


@responses.activate
def test_buzilgan_json_onecxato(mijoz):
    responses.get(f"{BAZA}/vositalar", body="{")

    with pytest.raises(OneCXato):
        mijoz.vositalar()


@responses.activate
def test_timeout_onecxato(mijoz):
    responses.get(f"{BAZA}/vositalar", body=requests.Timeout("juda sekin"))

    with pytest.raises(OneCXato):
        mijoz.vositalar()


@responses.activate
def test_ulanish_xatosi_onecxato(mijoz):
    responses.get(f"{BAZA}/vositalar", body=requests.ConnectionError("ulanmadi"))

    with pytest.raises(OneCXato):
        mijoz.vositalar()


@responses.activate
def test_basic_auth_yuboriladi(mijoz):
    responses.get(f"{BAZA}/versiya", json={})

    mijoz.versiya()

    sarlavha = responses.calls[0].request.headers["Authorization"]
    kutilgan = base64.b64encode(f"{LOGIN}:{PAROL}".encode()).decode()
    assert sarlavha == f"Basic {kutilgan}"


@responses.activate
def test_login_parol_url_va_xatoda_chiqmaydi():
    mijoz = OneCClient(BAZA, LOGIN, PAROL)
    responses.get(f"{BAZA}/vositalar", status=500, body=f"{LOGIN} {PAROL}")

    with pytest.raises(OneCXato) as istisno:
        mijoz.vositalar()

    assert LOGIN not in str(istisno.value) and PAROL not in str(istisno.value)
    url = responses.calls[0].request.url
    assert LOGIN not in url and PAROL not in url


@responses.activate
def test_timeout_uzatiladi():
    mijoz = OneCClient(BAZA, LOGIN, PAROL, timeout=7)
    responses.get(f"{BAZA}/versiya", json={})

    mijoz.versiya()

    assert responses.calls[0].request.req_kwargs["timeout"] == 7


@responses.activate
def test_oxiridagi_slesh_ikkilanmaydi():
    mijoz = OneCClient(f"{BAZA}/", LOGIN, PAROL)
    responses.get(f"{BAZA}/versiya", json={})

    mijoz.versiya()

    assert responses.calls[0].request.url == f"{BAZA}/versiya"


@responses.activate
def test_json_obyekt_emas_onecxato(mijoz):
    responses.get(f"{BAZA}/versiya", json=[1, 2])

    with pytest.raises(OneCXato):
        mijoz.versiya()


def test_settingsdan():
    with override_settings(ONEC_URL=BAZA, ONEC_LOGIN=LOGIN, ONEC_PAROL=PAROL):
        mijoz = OneCClient.settingsdan()

    assert mijoz.base_url == BAZA
    assert mijoz.login == LOGIN
    assert mijoz.parol == PAROL
