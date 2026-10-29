"""Umumiy sahifalash: sahifa raqamlari, «bir sahifada N qator» (sessiyada eslab qolinadi) — barcha ro'yxatlarda."""
import pytest
from django.urls import reverse

from vositalar.tests.test_bayroqlar import av_yarat

pytestmark = pytest.mark.django_db
ROYXAT = reverse("vositalar:royxat")


@pytest.fixture
def filial_a(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def client_hisobchi(client_rol):
    return client_rol("hisobchi")


@pytest.fixture
def avlar(filial_a):
    return [av_yarat(filial_a) for _ in range(23)]


def test_hajm_tanlanadi_va_eslab_qolinadi(client_hisobchi, avlar):
    javob = client_hisobchi.get(ROYXAT, {"hajm": "10"})
    sahifa = javob.context["sahifa"]
    assert len(sahifa.object_list) == 10 and sahifa.paginator.num_pages == 3
    # keyingi so'rovlarda (filtr formasi `hajm` yubormaydi) ham 10
    assert len(client_hisobchi.get(ROYXAT, {"q": ""}).context["sahifa"].object_list) == 10
    assert len(client_hisobchi.get(ROYXAT, {"hajm": "100"}).context["sahifa"].object_list) == 23


@pytest.mark.parametrize("qiymat, kutilgan", [("0", 1), ("-5", 1), ("abc", 23), ("100000", 23)])
def test_hajm_chegaralanadi(client_hisobchi, avlar, qiymat, kutilgan):
    assert len(client_hisobchi.get(ROYXAT, {"hajm": qiymat}).context["sahifa"].object_list) == kutilgan


def test_sahifa_raqamlari(client_hisobchi, filial_a):
    for _ in range(20):
        av_yarat(filial_a)
    javob = client_hisobchi.get(ROYXAT, {"hajm": "1", "page": "10", "q": ""})
    assert javob.context["sahifa"].raqamlar == [1, None, 8, 9, 10, 11, 12, None, 20]
    html = javob.content.decode()
    assert 'aria-current="page"><span class="page-link">10<' in html
    # havolalar filtr va hajmni saqlaydi; HTMX bilan jadval almashadi
    assert 'href="?hajm=1&amp;page=20&amp;q="' in html and 'hx-target="#jadval"' in html
    assert '<input type="hidden" name="q" value="">' in html and 'name="hajm"' in html and 'value="1"' in html


def test_boshqa_royxatlarda_ham(client_hisobchi, avlar):
    for nom in ("mol:akt_royxat", "reviziya:royxat", "chiqimlar:royxat"):
        javob = client_hisobchi.get(reverse(nom), {"hajm": "7"})
        assert javob.status_code == 200 and javob.context["sahifa"].hajm == 7, nom
    # har ro'yxat o'z hajmini eslaydi
    assert client_hisobchi.get(ROYXAT).context["sahifa"].hajm == 50
