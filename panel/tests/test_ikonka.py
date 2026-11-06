from django.contrib.staticfiles import finders

IKONKALAR = ["favicon.ico", "favicon-32.png", "icon-192.png", "apple-touch-icon.png"]


def test_ikonka_fayllari_bor():
    for nom in IKONKALAR:
        assert finders.find(f"panel/ikonka/{nom}"), nom


def test_kirish_sahifasida_ikonka(client):
    html = client.get("/kirish/").content.decode()
    assert "panel/ikonka/favicon.ico" in html and "panel/ikonka/apple-touch-icon.png" in html


def test_favicon_ildizdan_yonaltiriladi(client):
    javob = client.get("/favicon.ico")
    assert javob.status_code == 301 and javob.url.endswith("panel/ikonka/favicon.ico")
