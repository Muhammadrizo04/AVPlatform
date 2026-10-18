import pytest
from django.test import Client
from django.urls import reverse

from jurnal.models import Jurnal
from vositalar.amallar import AmalXato
from vositalar.bolimlar import bolim_nofaol_qil
from vositalar.models import Bolim
from vositalar.tests.test_bayroqlar import av_yarat, qator


@pytest.fixture
def filial_a(filial_yarat):
    return filial_yarat("A")


@pytest.fixture
def filial_b(filial_yarat):
    return filial_yarat("B")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def client_hisobchi(hisobchi):
    client = Client()
    client.force_login(hisobchi)
    return client


def saqla(client, filial, nomi, ota=None, bolim=None):
    return client.post(
        reverse("vositalar:bolim_saqla"),
        {"filial": filial.pk, "nomi": nomi, "ota": ota.pk if ota else "", "bolim": bolim.pk if bolim else ""},
    )


def test_daraxt_qoshish_va_nomlash(client_hisobchi, filial_a):
    assert saqla(client_hisobchi, filial_a, "Savdo zali").status_code == 200
    zal = Bolim.objects.get(nomi="Savdo zali")
    assert zal.ota is None and zal.filial == filial_a
    assert saqla(client_hisobchi, filial_a, "Kassa", ota=zal).status_code == 200
    kassa = Bolim.objects.get(nomi="Kassa")
    assert saqla(client_hisobchi, filial_a, "Kassa 2", ota=kassa).status_code == 200
    kassa2 = Bolim.objects.get(nomi="Kassa 2")
    assert kassa2.toliq_nomi == "Savdo zali / Kassa / Kassa 2"

    assert saqla(client_hisobchi, filial_a, "Kassa 1", ota=zal, bolim=kassa).status_code == 200
    kassa.refresh_from_db()
    assert kassa.nomi == "Kassa 1"
    sahifa = client_hisobchi.get(reverse("vositalar:bolimlar"), {"filial": filial_a.pk})
    assert "Kassa 2" in sahifa.content.decode()
    assert Jurnal.objects.filter(obyekt_turi="vositalar.bolim", obyekt_id=str(kassa.pk), maydon="nomi").exists()
    assert Jurnal.objects.filter(obyekt_turi="vositalar.bolim", obyekt_id=str(zal.pk)).exists()


def test_tsikl_va_oz_ichiga_kochirish_rad(client_hisobchi, filial_a):
    a = Bolim.objects.create(filial=filial_a, nomi="A")
    b = Bolim.objects.create(filial=filial_a, ota=a, nomi="B")
    for ota in (a, b):
        javob = saqla(client_hisobchi, filial_a, "A", ota=ota, bolim=a)
        assert javob.status_code == 400
    a.refresh_from_db()
    assert a.ota is None


def test_ota_boshqa_filialdan_rad(client_hisobchi, filial_a, filial_b):
    ota_b = Bolim.objects.create(filial=filial_b, nomi="B ota")
    javob = saqla(client_hisobchi, filial_a, "Yangi", ota=ota_b)
    assert javob.status_code == 400
    assert "boshqa filial" in javob.content.decode()
    assert not Bolim.objects.filter(nomi="Yangi").exists()


def test_ichida_av_bolsa_nofaol_bolmaydi(hisobchi, client_hisobchi, filial_a):
    ota = Bolim.objects.create(filial=filial_a, nomi="Ota")
    bola = Bolim.objects.create(filial=filial_a, ota=ota, nomi="Bola")
    av = av_yarat(filial_a)
    qator(av, filial_a, bolim=bola)

    with pytest.raises(AmalXato):
        bolim_nofaol_qil(ota, hisobchi)
    javob = client_hisobchi.post(reverse("vositalar:bolim_nofaol", args=[ota.pk]))
    assert javob.status_code == 400
    ota.refresh_from_db()
    bola.refresh_from_db()
    assert ota.faol and bola.faol


def test_nofaol_pastkilar_bilan_va_qayta_faollashtirish(hisobchi, client_hisobchi, filial_a):
    ota = Bolim.objects.create(filial=filial_a, nomi="Ota")
    bola = Bolim.objects.create(filial=filial_a, ota=ota, nomi="Bola")
    bolim_nofaol_qil(ota, hisobchi)
    ota.refresh_from_db()
    bola.refresh_from_db()
    assert not ota.faol and not bola.faol
    assert Jurnal.objects.filter(obyekt_turi="vositalar.bolim", maydon="faol").count() == 2

    # bola ota faolsiz paytda faollashmaydi, ota esa faollashadi
    assert client_hisobchi.post(reverse("vositalar:bolim_nofaol", args=[bola.pk])).status_code == 400
    assert client_hisobchi.post(reverse("vositalar:bolim_nofaol", args=[ota.pk])).status_code == 200
    ota.refresh_from_db()
    assert ota.faol


def test_bolim_av_royxati_soni_bilan(client_hisobchi, filial_a):
    bolim = Bolim.objects.create(filial=filial_a, nomi="Ombor")
    boshqa = Bolim.objects.create(filial=filial_a, nomi="Boshqa")
    av = av_yarat(filial_a, soni="5")
    qator(av, filial_a, soni="2", bolim=bolim)
    from vositalar.models import Holat, Taqsimot
    Taqsimot.objects.create(av=av, filial=filial_a, bolim=bolim, holat=Holat.NOSOZ, soni=1)
    qator(av, filial_a, soni="2", bolim=boshqa)

    javob = client_hisobchi.get(reverse("vositalar:bolimlar"), {"filial": filial_a.pk, "bolim": bolim.pk})
    matn = javob.content.decode()
    assert reverse("vositalar:kartochka", args=[av.pk]) in matn
    assert [(a.pk, a.bolim_soni) for a in javob.context["avlar"]] == [(av.pk, 3)]


def test_hr_bolim_tahrirlolmaydi(client_rol, filial_a):
    hr = client_rol("hr")
    bolim = Bolim.objects.create(filial=filial_a, nomi="X")
    assert hr.get(reverse("vositalar:bolimlar")).status_code == 200
    assert saqla(hr, filial_a, "Yangi").status_code == 403
    assert hr.post(reverse("vositalar:bolim_nofaol", args=[bolim.pk])).status_code == 403
    assert not Bolim.objects.filter(nomi="Yangi").exists()


def test_ruxsatsiz_filial_404(cheklangan_client_yarat, filial_a, filial_b):
    client = cheklangan_client_yarat(filial_a)
    bolim_b = Bolim.objects.create(filial=filial_b, nomi="B")
    sahifa = client.get(reverse("vositalar:bolimlar"))
    assert [f.pk for f in sahifa.context["filiallar"]] == [filial_a.pk]
    assert client.get(reverse("vositalar:bolimlar"), {"filial": filial_b.pk}).status_code == 404
    assert saqla(client, filial_b, "Yangi").status_code == 404
    assert client.post(reverse("vositalar:bolim_nofaol", args=[bolim_b.pk])).status_code == 404
    # ruxsatli filialga boshqa filial bo'limini ota qilib berish ham ko'rinmaydi
    assert saqla(client, filial_a, "Yangi", ota=bolim_b).status_code in (400, 404)
    bolim_b.refresh_from_db()
    assert bolim_b.faol
    assert not Bolim.objects.filter(nomi="Yangi").exists()


@pytest.fixture
def cheklangan_client_yarat(foydalanuvchi):
    def yarat(*filiallar):
        client = Client()
        client.force_login(foydalanuvchi("hisobchi", list(filiallar)))
        return client

    return yarat


def test_nomlash_otani_ozgartirmaydi(client_hisobchi, filial_a):
    ota = Bolim.objects.create(filial=filial_a, nomi="Ota", faol=False)
    bola = Bolim.objects.create(filial=filial_a, ota=ota, nomi="Bola")
    javob = client_hisobchi.post(
        reverse("vositalar:bolim_saqla"), {"filial": filial_a.pk, "bolim": bola.pk, "nomi": "Yangi nom"}
    )
    assert javob.status_code == 200
    bola.refresh_from_db()
    assert bola.nomi == "Yangi nom" and bola.ota_id == ota.pk
    assert not Jurnal.objects.filter(obyekt_turi="vositalar.bolim", obyekt_id=str(bola.pk), maydon="ota").exists()

    # aniq ildiz tanlovi (ota="") esa ko'chiradi
    assert saqla(client_hisobchi, filial_a, "Yangi nom", bolim=bola).status_code == 200
    bola.refresh_from_db()
    assert bola.ota_id is None


def test_forma_tanlangan_bolim_bilan_toldiriladi(client_hisobchi, filial_a):
    ota = Bolim.objects.create(filial=filial_a, nomi="Ota", faol=False)
    bola = Bolim.objects.create(filial=filial_a, ota=ota, nomi="Bola")
    matn = client_hisobchi.get(
        reverse("vositalar:bolimlar"), {"filial": filial_a.pk, "bolim": bola.pk}
    ).content.decode()
    assert f'<option value="{ota.pk}" selected>' in matn
    assert f'<input type="hidden" name="bolim" value="{bola.pk}">' in matn
    assert 'name="nomi" maxlength="255" value="Bola"' in matn
    assert "<select name=\"bolim\"" not in matn  # erkin bo'lim tanlash yo'q: tahrirlanadigan bo'lim oldindan tanlangan


def test_daraxt_sorovlari_chuqurlikka_bogliq_emas(client_hisobchi, filial_a):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def sorovlar():
        with CaptureQueriesContext(connection) as ctx:
            assert client_hisobchi.get(reverse("vositalar:bolimlar"), {"filial": filial_a.pk}).status_code == 200
        return len(ctx)

    ota = None
    for i in range(3):
        ota = Bolim.objects.create(filial=filial_a, ota=ota, nomi=f"D{i}")
    uch = sorovlar()
    for i in range(3, 8):
        ota = Bolim.objects.create(filial=filial_a, ota=ota, nomi=f"D{i}")
    assert sorovlar() == uch


def test_aniq_joriy_nofaol_ota_qabul_qilinadi(client_hisobchi, filial_a):
    ota = Bolim.objects.create(filial=filial_a, nomi="Ota", faol=False)
    bola = Bolim.objects.create(filial=filial_a, ota=ota, nomi="Bola")
    javob = saqla(client_hisobchi, filial_a, "Yangi nom", ota=ota, bolim=bola)
    assert javob.status_code == 200
    bola.refresh_from_db()
    assert bola.nomi == "Yangi nom" and bola.ota_id == ota.pk
    assert not Jurnal.objects.filter(obyekt_turi="vositalar.bolim", obyekt_id=str(bola.pk), maydon="ota").exists()
    # yangi ota esa faol bo'lishi shart
    boshqa = Bolim.objects.create(filial=filial_a, nomi="Boshqa", faol=False)
    assert saqla(client_hisobchi, filial_a, "Yangi nom", ota=boshqa, bolim=bola).status_code == 400
