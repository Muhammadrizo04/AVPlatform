import base64

import pytest
from django.contrib.staticfiles import finders
from django.template.loader import get_template

from panel.logotip import logotip_uri

pytestmark = pytest.mark.django_db


def test_logotip_fayli_static_da():
    # media/ git'ga kirmaydi: logotip serverga yetishi uchun static'da turishi shart
    assert finders.find("panel/logotip.png")


def test_logotip_uri_png():
    bosh, malumot = logotip_uri().split(",", 1)
    assert bosh == "data:image/png;base64"
    assert base64.b64decode(malumot).startswith(b"\x89PNG")


def test_kirish_sahifasida_logotip(client):
    assert "panel/logotip.png" in client.get("/kirish/").content.decode()


def test_chop_logotipi_ekranda_yashirin():
    css = open(finders.find("panel/panel.css"), encoding="utf8").read()
    assert ".chop-logotip { display: none; }" in css


@pytest.mark.parametrize("shablon", ["mol/akt_pdf.html", "reviziya/dalolatnoma_pdf.html"])
def test_pdf_sarlavhasida_logotip(shablon):
    assert '<img src="{{ logotip }}"' in get_template(shablon).template.source
