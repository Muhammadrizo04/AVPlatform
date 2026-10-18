import io
import uuid
from decimal import Decimal

import pytest
from pypdf import PdfReader

from mol.models import MolAkt
from mol.pdf import akt_pdf
from mol.servis import AktXato, akt_tasdiqla, akt_yarat
from onec.models import AV, AVQoldiq, Xodim
from vositalar.amallar import kochir
from vositalar.models import Bolim, Holat, Sozlama, Taqsimot, TaqsimotHarakat

SON = Decimal


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def user(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def bobur(filial):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Bobur", filial=filial)


@pytest.fixture
def aziz(filial):
    return Xodim.objects.create(ref_1c=uuid.uuid4(), ism="Aziz", filial=filial)


@pytest.fixture
def ombor(filial):
    return Bolim.objects.create(filial=filial, nomi="Ombor")


def av_yarat(filial, soni="6", kod="1", nomi="Stol"):
    av = AV.objects.create(ref_1c=uuid.uuid4(), kod=kod, nomi=nomi, inv_raqam=f"INV-{kod}")
    AVQoldiq.objects.create(av=av, filial=filial, soni=SON(soni), summa=SON("600"))
    return av


def qator(av, filial, soni, bolim=None, mol=None, holat=Holat.ISHLATILMOQDA):
    return Taqsimot.objects.create(av=av, filial=filial, bolim=bolim, mol=mol, holat=holat, soni=SON(soni))


def soni_of(av, mol):
    return sum(t.soni for t in Taqsimot.objects.filter(av=av, mol=mol))


def test_akt_yarat_qoralama(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)

    akt = akt_yarat(bobur, aziz, [(q, SON("6"))], user, izoh="Yangi xodim")

    assert akt.holat == MolAkt.Holat.QORALAMA
    assert akt.qatorlar.count() == 1
    assert (akt.topshiruvchi, akt.qabul_qiluvchi, akt.tuzdi) == (bobur, aziz, user)
    assert akt.nomi == f"MA-{akt.raqam:06d}"
    q.refresh_from_db()
    assert q.mol == bobur and q.soni == SON("6")
    assert not Taqsimot.objects.filter(mol=aziz).exists()


def test_tasdiqlash_mol_ozgaradi(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("6"))], user)

    akt_tasdiqla(akt, user)

    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.TASDIQLANGAN
    assert akt.tasdiqladi == user and akt.tasdiq_vaqti is not None
    assert soni_of(av, aziz) == SON("6")
    assert soni_of(av, bobur) == 0
    assert not Taqsimot.objects.filter(pk=q.pk).exists()
    harakat = TaqsimotHarakat.objects.get(sabab=TaqsimotHarakat.Sabab.MOL_AKT)
    assert harakat.hujjat_izoh == akt.nomi


def test_qisman_soni(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("4"))], user)

    akt_tasdiqla(akt, user)

    assert soni_of(av, bobur) == SON("2")
    assert soni_of(av, aziz) == SON("4")


def test_birinchi_biriktirish(filial, user, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, None)
    akt = akt_yarat(None, aziz, [(q, SON("6"))], user)

    akt_tasdiqla(akt, user)

    assert soni_of(av, aziz) == SON("6")
    assert not Taqsimot.objects.filter(mol=None).exists()


def test_qabul_qiluvchi_ishdan_ketgan_rad(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("6"))], user)
    Xodim.objects.filter(pk=aziz.pk).update(ishdan_bushagan=True)

    with pytest.raises(AktXato):
        akt_tasdiqla(akt, user)

    akt.refresh_from_db()
    assert akt.holat == MolAkt.Holat.QORALAMA
    q.refresh_from_db()
    assert q.mol == bobur and q.soni == SON("6")
    assert not Taqsimot.objects.filter(mol=aziz).exists()


@pytest.mark.parametrize("maydon", ["neaktiv", "onec_da_yoq"])
def test_qabul_qiluvchi_neaktiv_rad(filial, user, bobur, aziz, ombor, maydon):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("6"))], user)
    Xodim.objects.filter(pk=aziz.pk).update(**{maydon: True})

    with pytest.raises(AktXato):
        akt_tasdiqla(akt, user)

    assert soni_of(av, bobur) == SON("6")


def test_arxiv_av_rad(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("6"))], user)
    AVQoldiq.objects.filter(av=av).update(soni=SON("0"))

    with pytest.raises(AktXato):
        akt_tasdiqla(akt, user)

    assert soni_of(av, bobur) == SON("6")


def test_tasdiqlashgacha_qator_ozgargan(filial, user, bobur, aziz, ombor):
    av1 = av_yarat(filial, kod="1")
    av2 = av_yarat(filial, kod="2", nomi="Stul")
    q1 = qator(av1, filial, "6", ombor, bobur)
    q2 = qator(av2, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q1, SON("6")), (q2, SON("6"))], user)
    ofis = Bolim.objects.create(filial=filial, nomi="Ofis")
    kochir(q2, SON("6"), ofis, user)  # q2 boshqa bo'limga ko'chdi

    with pytest.raises(AktXato):
        akt_tasdiqla(akt, user)

    assert soni_of(av1, bobur) == SON("6")
    assert soni_of(av2, bobur) == SON("6")
    assert not Taqsimot.objects.filter(mol=aziz).exists()
    assert MolAkt.objects.get(pk=akt.pk).holat == MolAkt.Holat.QORALAMA


def test_bir_qator_ikki_marta(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("4")), (q, SON("4"))], user)

    with pytest.raises(AktXato):
        akt_tasdiqla(akt, user)

    assert soni_of(av, bobur) == SON("6")
    assert soni_of(av, aziz) == 0


def test_tasdiqlangan_akt_qayta_tasdiqlanmaydi(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("3"))], user)
    akt_tasdiqla(akt, user)

    with pytest.raises(AktXato):
        akt_tasdiqla(akt, user)

    assert soni_of(av, aziz) == SON("3")


def test_akt_yarat_notogri_qator(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, aziz)  # Bobur'da emas
    with pytest.raises(AktXato):
        akt_yarat(bobur, aziz, [(q, SON("1"))], user)
    q2 = qator(av, filial, "1", ombor, bobur, holat=Holat.NOSOZ)
    with pytest.raises(AktXato):
        akt_yarat(bobur, aziz, [(q2, SON("2"))], user)  # mavjuddan ko'p
    with pytest.raises(AktXato):
        akt_yarat(bobur, aziz, [], user)
    assert MolAkt.objects.count() == 0


def test_raqam_ketma_ket(filial, user, bobur, aziz, ombor):
    av = av_yarat(filial)
    q = qator(av, filial, "6", ombor, bobur)
    a1 = akt_yarat(bobur, aziz, [(q, SON("1"))], user)
    a2 = akt_yarat(bobur, aziz, [(q, SON("1"))], user)
    assert a2.raqam == a1.raqam + 1
    assert a1.nomi == "MA-000001"


def test_pdf_baytlar(filial, user, bobur, aziz, ombor):
    Sozlama.objects.update_or_create(pk=1, defaults={"kompaniya_nomi": "Ўзбек Савдо MCHJ"})
    av = av_yarat(filial, nomi="Стол офисный")
    q = qator(av, filial, "6", ombor, bobur)
    akt = akt_yarat(bobur, aziz, [(q, SON("4"))], user)

    pdf = akt_pdf(akt)

    assert pdf.startswith(b"%PDF")
    matn = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert akt.nomi in matn
    assert "Bobur" in matn and "Aziz" in matn and "INV-1" in matn
    assert "400.00" in matn  # 4 dona x (600 / 6)


def test_raqam_advisory_lock_bilan(filial, user, bobur, aziz, ombor):
    """Akt raqami advisory lock (7310002) ostida beriladi: lock band bo'lsa akt yaratish kutadi."""
    import psycopg
    from django.db import OperationalError, connection

    from mol.servis import AKT_RAQAM_QULFI

    assert AKT_RAQAM_QULFI == 7310002
    q = qator(av_yarat(filial), filial, "6", ombor, bobur)
    s = connection.settings_dict
    with psycopg.connect(
        dbname=s["NAME"], user=s["USER"], password=s["PASSWORD"],
        host=s["HOST"] or None, port=s["PORT"] or None, autocommit=True,
    ) as boshqa:
        boshqa.execute("SELECT pg_advisory_lock(%s)", [AKT_RAQAM_QULFI])
        try:
            with connection.cursor() as c:
                c.execute("SET lock_timeout = '300ms'")
            try:
                with pytest.raises(OperationalError):
                    akt_yarat(bobur, aziz, [(q, SON("1"))], user)
            finally:
                with connection.cursor() as c:
                    c.execute("SET lock_timeout = 0")
        finally:
            boshqa.execute("SELECT pg_advisory_unlock(%s)", [AKT_RAQAM_QULFI])
    assert not MolAkt.objects.exists()
    assert akt_yarat(bobur, aziz, [(q, SON("1"))], user).raqam == 1
