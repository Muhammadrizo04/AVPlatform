"""«Xususiyat bo'yicha qidiruv»: kartochkadagi qo'shimcha maydonlar bo'yicha AV'lar qayerda va nechta."""
import io
import uuid
from decimal import Decimal as D

import pytest
from django.urls import reverse
from openpyxl import load_workbook

from hisobotlar.xususiyat import qidir, qiymatlar
from onec.models import AVTuri
from vositalar.models import AVKartochka, AVTuriSozlama
from vositalar.tests.test_bayroqlar import av_yarat, qator, xodim

pytestmark = pytest.mark.django_db

URL = "hisobotlar:xususiyat"
MAYDONLAR = [
    {"kalit": "turi", "nomi": "Qurilma", "tip": "tanlov", "tanlov_qiymatlari": ["Noutbuk", "PC"]},
    {"kalit": "ram", "nomi": "RAM", "tip": "tanlov", "tanlov_qiymatlari": ["8 GB", "16 GB", "16 GB (8 + 8)"]},
    {"kalit": "xotira", "nomi": "Storage", "tip": "xotira", "tanlov_qiymatlari": []},
    {"kalit": "gpu", "nomi": "GPU", "tip": "matn", "tanlov_qiymatlari": []},
]


@pytest.fixture
def kompyuter():
    tur = AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="KOMPYUTERLAR")
    AVTuriSozlama.objects.create(av_turi=tur, maydonlar=MAYDONLAR)
    return tur


@pytest.fixture
def x(filial_yarat):
    return filial_yarat("01")


@pytest.fixture
def y(filial_yarat):
    return filial_yarat("02")


def kompyuter_yarat(tur, filial, soni="1", mol=None, **qoshimcha):
    av = av_yarat(filial, inv=uuid.uuid4().hex[:8], soni=soni, turi=tur)
    AVKartochka.objects.create(av=av, qoshimcha=qoshimcha)
    return qator(av, filial, soni, mol=mol)


@pytest.mark.parametrize("tip, qiymat, kutilgan", [
    ("tanlov", "16 GB", {"16 GB"}),
    ("tanlov", "16 GB (8 + 8)", {"16 GB"}),
    ("tanlov", "16GB", {"16 GB"}),
    ("tanlov", "1 TB", {"1 TB"}),
    ("tanlov", "Noutbuk", {"Noutbuk"}),
    ("matn", "4 GB GTX 1650", {"4 GB GTX 1650"}),
    ("xotira", "M.2 SSD 512 GB + HDD 1 TB", {"512 GB", "1 TB"}),
    ("tanlov", "", set()),
    ("matn", None, set()),
])
def test_qiymatlar_guruhlanadi(tip, qiymat, kutilgan):
    assert qiymatlar(tip, qiymat) == kutilgan


def test_ram_yozilishi_har_xil_bolsa_ham_topiladi(foydalanuvchi, kompyuter, x):
    a = kompyuter_yarat(kompyuter, x, ram="16 GB")
    b = kompyuter_yarat(kompyuter, x, ram="16 GB (8 + 8)")
    kompyuter_yarat(kompyuter, x, ram="8 GB")

    assert {t.pk for t in qidir(foydalanuvchi("admin"), {"m_ram": "16 GB"}).qatorlar} == {a.pk, b.pk}


def test_bir_nechta_xususiyat_birga_ishlaydi(foydalanuvchi, kompyuter, x):
    a = kompyuter_yarat(kompyuter, x, ram="16 GB", turi="Noutbuk")
    kompyuter_yarat(kompyuter, x, ram="16 GB", turi="PC")

    natija = qidir(foydalanuvchi("admin"), {"m_ram": "16 GB", "m_turi": "Noutbuk"})

    assert [t.pk for t in natija.qatorlar] == [a.pk]


def test_storage_hajmi_boyicha(foydalanuvchi, kompyuter, x):
    a = kompyuter_yarat(kompyuter, x, xotira="HDD 1 TB + M.2 SSD 512 GB")
    kompyuter_yarat(kompyuter, x, xotira="HDD 1 TB")

    assert [t.pk for t in qidir(foydalanuvchi("admin"), {"m_xotira": "512 GB"}).qatorlar] == [a.pk]


def test_filiallar_boyicha_dona_soni(foydalanuvchi, kompyuter, x, y):
    kompyuter_yarat(kompyuter, x, soni="2", ram="16 GB")
    kompyuter_yarat(kompyuter, x, ram="16 GB")
    kompyuter_yarat(kompyuter, y, ram="16 GB")

    natija = qidir(foydalanuvchi("admin"), {"m_ram": "16 GB"})

    assert natija.jami == D("4")
    assert natija.filiallar == [(x.nomi, D("3")), (y.nomi, D("1"))]


def test_faqat_ruxsat_etilgan_filial(foydalanuvchi, kompyuter, x, y):
    kompyuter_yarat(kompyuter, x, ram="16 GB")
    kompyuter_yarat(kompyuter, y, ram="16 GB")
    u = foydalanuvchi("hisobchi", filiallar=[x])

    natija = qidir(u, {"m_ram": "16 GB"})

    assert natija.jami == 1 and natija.filiallar == [(x.nomi, D("1"))]
    assert dict(natija.maydonlar[0]["variantlar"])["16 GB"] == 1


def test_boshqa_filial_tanlansa_ruxsatsiz_natija_chiqmaydi(foydalanuvchi, kompyuter, x, y):
    kompyuter_yarat(kompyuter, y, ram="16 GB")

    assert qidir(foydalanuvchi("hisobchi", filiallar=[x]), {"m_ram": "16 GB", "filial": str(y.pk)}).jami == 0


def test_filial_va_holat_filtri(foydalanuvchi, kompyuter, x, y):
    kompyuter_yarat(kompyuter, x, ram="16 GB")
    a = kompyuter_yarat(kompyuter, y, ram="16 GB")
    u = foydalanuvchi("admin")

    assert [t.pk for t in qidir(u, {"m_ram": "16 GB", "filial": str(y.pk)}).qatorlar] == [a.pk]
    assert qidir(u, {"m_ram": "16 GB", "holat": "nosoz"}).jami == 0


def test_kiritilmagan_soni_korsatiladi(foydalanuvchi, kompyuter, x):
    kompyuter_yarat(kompyuter, x, ram="16 GB")
    kompyuter_yarat(kompyuter, x, soni="3")
    kompyuter_yarat(kompyuter, x, ram="8 GB")

    assert qidir(foydalanuvchi("admin"), {"m_ram": "16 GB"}).kiritilmagan == D("3")


def test_maydoni_yoq_tur_kiritilmagan_hisoblanmaydi(foydalanuvchi, kompyuter, x):
    qator(av_yarat(x, inv="stul", turi=AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi="Mebel")), x, "5")

    assert qidir(foydalanuvchi("admin"), {"m_ram": "16 GB"}).kiritilmagan == 0


def test_variantlar_tanlovga_mos_sanaladi(foydalanuvchi, kompyuter, x):
    kompyuter_yarat(kompyuter, x, ram="16 GB", turi="Noutbuk")
    kompyuter_yarat(kompyuter, x, ram="8 GB", turi="PC")

    natija = qidir(foydalanuvchi("admin"), {"m_turi": "Noutbuk"})

    ram = next(m for m in natija.maydonlar if m["kalit"] == "ram")
    qurilma = next(m for m in natija.maydonlar if m["kalit"] == "turi")
    assert dict(ram["variantlar"]) == {"16 GB": 1}
    assert dict(qurilma["variantlar"]) == {"Noutbuk": 1, "PC": 1}


def test_variantlar_hajm_boyicha_tartiblanadi(foydalanuvchi, kompyuter, x):
    for ram in ("16 GB", "8 GB", "1 TB", "32 GB"):
        kompyuter_yarat(kompyuter, x, ram=ram)

    ram = next(m for m in qidir(foydalanuvchi("admin"), {}).maydonlar if m["kalit"] == "ram")

    assert [v for v, _ in ram["variantlar"]] == ["8 GB", "16 GB", "32 GB", "1 TB"]


def test_tanlov_bolmasa_natija_chiqmaydi(foydalanuvchi, kompyuter, x):
    kompyuter_yarat(kompyuter, x, ram="16 GB")

    natija = qidir(foydalanuvchi("admin"), {})

    assert natija.qatorlar == [] and not natija.tanlangan


def test_notogri_parametrlar_xato_bermaydi(foydalanuvchi, kompyuter, x):
    kompyuter_yarat(kompyuter, x, ram="16 GB")

    natija = qidir(foydalanuvchi("admin"), {"m_yoq": "1", "filial": "abc", "turi": "x", "holat": "yoq", "m_ram": "99 GB"})

    assert natija.jami == 0


def test_sahifada_filial_javobgar_va_xususiyat_chiqadi(client_rol, kompyuter, x):
    kompyuter_yarat(kompyuter, x, mol=xodim(filial=x), ram="16 GB (8 + 8)")

    html = client_rol("hr").get(reverse(URL), {"m_ram": "16 GB"}).content.decode()

    assert x.nomi in html and "Ali" in html and "16 GB (8 + 8)" in html


def test_ma_lumot_yoq_bolsa_tushuntiriladi(client_rol, kompyuter):
    assert "kiritilmagan" in client_rol("admin").get(reverse(URL)).content.decode()


def test_excel(client_rol, kompyuter, x):
    t = kompyuter_yarat(kompyuter, x, ram="16 GB (8 + 8)")

    javob = client_rol("hisobchi").get(reverse(URL), {"m_ram": "16 GB", "format": "xlsx"})

    qatorlar = list(load_workbook(io.BytesIO(javob.content)).active.iter_rows(values_only=True))
    assert "RAM" in qatorlar[0] and t.av.inv_raqam in qatorlar[1] and "16 GB (8 + 8)" in qatorlar[1]


def test_revizorga_yopiq(client_rol):
    assert client_rol("revizor").get(reverse(URL)).status_code == 403


def test_menyuda_bor(client_rol):
    assert reverse(URL) in client_rol("hisobchi").get(reverse("hisobotlar:kesim")).content.decode()
