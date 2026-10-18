import copy
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from onec.client import OneCXato
from onec.models import AV, AVQoldiq, AVTuri, Filial, Harakat1C, SinxronJurnal, Tashkilot, Xodim
from onec.sinxron import SinxronBand, ketma_ket_xatolar, oxirgi_muvaffaqiyatli, sinxronla

NAMUNALAR = Path(__file__).parent / "namunalar"
TOSHKENT = ZoneInfo("Asia/Tashkent")
# Namunadagi harakatlar 2026-09 oyida: 45 kunlik oyna ularning hammasini qamraydi.
HOZIR = datetime(2026, 10, 1, 12, 0, tzinfo=TOSHKENT)
QULF = 7310001
CHEKSIZ_GACHA = datetime(3999, 12, 31, 23, 59, 59)
LOGIN = "sinov-login"
PAROL = "sinov-parol-98765"

pytestmark = pytest.mark.django_db


def namuna(nom):
    return json.loads((NAMUNALAR / f"{nom}.json").read_text(encoding="utf-8"))


class SoxtaClient:
    """OneCClient o'rnini bosuvchi: namunalarni qaytaradi, harakatlarni dan/gacha bo'yicha suzadi."""

    def __init__(self):
        self.login = LOGIN
        self.parol = PAROL
        self.sprav = namuna("spravochniklar")
        self.vos = namuna("vositalar")
        self.har = namuna("harakatlar")["harakatlar"]
        self.vositalar_xatosi = None
        self.harakat_sorovlari = []
        self.parametrlarni_etiborsiz = False  # 1C dan/gacha'ni e'tiborsiz qoldirsa

    def spravochniklar(self):
        return copy.deepcopy(self.sprav)

    def vositalar(self):
        if self.vositalar_xatosi:
            raise self.vositalar_xatosi
        return copy.deepcopy(self.vos)

    def harakatlar(self, dan, gacha):
        # 1C sanalari — Toshkent vaqti, zonasiz.
        assert dan.tzinfo is None and gacha.tzinfo is None
        self.harakat_sorovlari.append((dan, gacha))
        return [
            copy.deepcopy(h)
            for h in self.har
            if self.parametrlarni_etiborsiz or h["sana"] is None
            or dan <= datetime.fromisoformat(h["sana"]) <= gacha
        ]


def yaroqli_qoldiqlar(client):
    av_reflar = {v["ref"] for v in client.vos["vositalar"]}
    return [q for q in client.vos["qoldiqlar"] if q["filial"] and q["av"] in av_reflar]


def yaroqli_harakatlar(client):
    av_reflar = {v["ref"] for v in client.vos["vositalar"]}
    return [
        h for h in client.har
        if h["sana"] and h["hujjat_ref"] and h["av"] in av_reflar and h["vid"] in ("kirim", "chiqim")
    ]


def mahalliy_iso(vaqt):
    return vaqt.astimezone(TOSHKENT).replace(tzinfo=None).isoformat()


def namuna_harakat(client, sana):
    """Namunadagi birinchi harakat nusxasi, boshqa sana va hujjat bilan."""
    h = copy.deepcopy(client.har[0])
    h["sana"] = mahalliy_iso(sana)
    h["hujjat_ref"] = str(uuid.uuid4())
    return h


def soxta_harakat(av, sana):
    return Harakat1C.objects.create(
        sana=sana, hujjat_turi="Sinov", hujjat_raqami="1", hujjat_ref=uuid.uuid4(),
        av=av, vid="kirim", soni=1, summa=0,
    )


def test_birinchi_sinxron_hammasini_yaratadi():
    client = SoxtaClient()

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.OK
    assert jurnal.tugadi is not None
    assert Tashkilot.objects.count() == len(client.sprav["tashkilotlar"])
    assert Filial.objects.count() == len(client.sprav["filiallar"])
    assert AVTuri.objects.count() == len(client.sprav["av_turlari"])
    assert Xodim.objects.count() == len(client.sprav["xodimlar"])
    assert AV.objects.count() == len(client.vos["vositalar"])
    assert AVQoldiq.objects.count() == len(yaroqli_qoldiqlar(client))
    assert Harakat1C.objects.count() == len(yaroqli_harakatlar(client))
    assert jurnal.ozgarishlar["av"]["yaratildi"] == len(client.vos["vositalar"])

    # Maydonlar kontrakt bo'yicha joylashgan.
    v = next(
        x for x in client.vos["vositalar"]
        if x["turi"] and x["filial"] and x["tashkilot"] and x["chiqarilgan_sana"]
    )
    av = AV.objects.get(ref_1c=v["ref"])
    assert (av.kod, av.nomi, av.inv_raqam, av.izoh_1c) == (v["kod"], v["nomi"], v["inv_raqam"], v["izoh"])
    assert str(av.chiqarilgan_sana) == v["chiqarilgan_sana"]
    assert str(av.turi.ref_1c) == v["turi"]
    assert str(av.tashkilot.ref_1c) == v["tashkilot"]
    assert str(av.filial_rekvizit.ref_1c) == v["filial"]
    assert not av.onec_da_yoq and av.sinx_vaqti is not None

    # 1C sanasi Toshkent vaqti deb saqlangan.
    h = yaroqli_harakatlar(client)[0]
    harakat = Harakat1C.objects.filter(hujjat_ref=h["hujjat_ref"]).first()
    assert harakat.sana == datetime.fromisoformat(h["sana"]).replace(tzinfo=TOSHKENT)


def test_takroriy_sinxron_ozgarmaydi():
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    modellar = [Tashkilot, Filial, AVTuri, Xodim, AV, AVQoldiq, Harakat1C]
    oldin = [m.objects.count() for m in modellar]

    jurnal = sinxronla(client, hozir=HOZIR)

    assert [m.objects.count() for m in modellar] == oldin
    for kalit in ("tashkilot", "filial", "av_turi", "xodim", "av"):
        assert jurnal.ozgarishlar[kalit] == {"yaratildi": 0, "yangilandi": 0, "yoqoldi": 0}


def test_yoqolgan_xodim_belgilanadi():
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    olingan = client.sprav["xodimlar"].pop(0)

    jurnal = sinxronla(client, hozir=HOZIR)

    xodim = Xodim.objects.get(ref_1c=olingan["ref"])
    assert xodim.onec_da_yoq is True
    assert Xodim.objects.count() == len(client.sprav["xodimlar"]) + 1
    assert Xodim.objects.filter(onec_da_yoq=False).count() == len(client.sprav["xodimlar"])
    assert jurnal.ozgarishlar["xodim"]["yoqoldi"] == 1

    # 1C'da qayta paydo bo'lsa — bayroq olinadi.
    client.sprav["xodimlar"].append(olingan)
    sinxronla(client, hozir=HOZIR)
    xodim.refresh_from_db()
    assert xodim.onec_da_yoq is False


def test_harakat_oynasi_eskini_saqlaydi():
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    av = AV.objects.first()
    eski = soxta_harakat(av, HOZIR - timedelta(days=60))
    oynadagi = soxta_harakat(av, HOZIR - timedelta(days=10))  # 1C'da yo'q -> o'chishi kerak

    sinxronla(client, hozir=HOZIR)

    assert Harakat1C.objects.filter(pk=eski.pk).exists()
    assert not Harakat1C.objects.filter(pk=oynadagi.pk).exists()
    assert Harakat1C.objects.count() == len(yaroqli_harakatlar(client)) + 1
    dan, gacha = client.harakat_sorovlari[-1]
    assert dan == (HOZIR - timedelta(days=45)).replace(tzinfo=None)
    assert gacha == CHEKSIZ_GACHA


def test_kelajakdagi_harakat_saqlanadi():
    client = SoxtaClient()
    kelajak = namuna_harakat(client, HOZIR + timedelta(days=5))
    client.har.append(kelajak)

    sinxronla(client, hozir=HOZIR)
    sinxronla(client, hozir=HOZIR)

    assert Harakat1C.objects.filter(hujjat_ref=kelajak["hujjat_ref"]).count() == 1
    assert Harakat1C.objects.count() == len(yaroqli_harakatlar(client))


def test_oraliqdan_tashqari_harakat_otkaziladi():
    client = SoxtaClient()
    oyna_boshi = (HOZIR - timedelta(days=45)).astimezone(TOSHKENT).replace(tzinfo=None)
    yaroqli = yaroqli_harakatlar(client)
    oynadan_tashqari = sum(datetime.fromisoformat(h["sana"]) < oyna_boshi for h in yaroqli)
    sinxronla(client, hozir=HOZIR)
    eski = soxta_harakat(AV.objects.first(), HOZIR - timedelta(days=60))
    client.har.append(namuna_harakat(client, HOZIR - timedelta(days=60)))
    client.parametrlarni_etiborsiz = True

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.ozgarishlar["harakat_otkazildi"] == oynadan_tashqari + 1
    assert Harakat1C.objects.filter(pk=eski.pk).exists()
    assert Harakat1C.objects.count() == len(yaroqli) + 1


def test_nomalum_vid_otkaziladi():
    client = SoxtaClient()
    client.har[0]["vid"] = None
    client.har[1]["vid"] = "boshqa"

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.OK, jurnal.xato_matni
    assert jurnal.ozgarishlar["harakat_otkazildi"] == 2
    assert Harakat1C.objects.count() == len(yaroqli_harakatlar(client))


def test_toliq_sinxron_hammasini_almashtiradi():
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    eski = soxta_harakat(AV.objects.first(), HOZIR - timedelta(days=400))

    jurnal = sinxronla(client, toliq=True, hozir=HOZIR)

    assert jurnal.toliq is True
    assert not Harakat1C.objects.filter(pk=eski.pk).exists()
    assert Harakat1C.objects.count() == len(yaroqli_harakatlar(client))
    dan, _ = client.harakat_sorovlari[-1]
    assert dan.year <= 1900


def test_xatoda_rollback():
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    av_soni = AV.objects.count()
    client.vos["vositalar"].pop()
    client.vositalar_xatosi = OneCXato("1C HTTP 500 qaytardi: /vositalar")

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.XATO
    assert "1C HTTP 500 qaytardi: /vositalar" in jurnal.xato_matni
    assert jurnal.tugadi is not None
    assert AV.objects.count() == av_soni
    assert AV.objects.filter(onec_da_yoq=True).count() == 0


def test_tranzaksiya_ichidagi_xato_rollback(monkeypatch):
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    filial = client.sprav["filiallar"][0]
    filial["nomi"] = "Yangi nom"
    client.sprav["filiallar"].append({"ref": str(uuid.uuid4()), "kod": "999", "nomi": "Yangi filial"})

    def buzilgan():
        raise RuntimeError("moslashda xato")

    monkeypatch.setattr("onec.sinxron.moslashtir", buzilgan)

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.XATO
    assert "moslashda xato" in jurnal.xato_matni
    assert Filial.objects.count() == len(client.sprav["filiallar"]) - 1
    assert Filial.objects.get(ref_1c=filial["ref"]).nomi != "Yangi nom"


def test_xato_matnida_parol_yoq():
    client = SoxtaClient()
    client.vositalar_xatosi = OneCXato(f"http://{LOGIN}:{PAROL}@1c/hs/av/vositalar ulanmadi")

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.XATO
    assert PAROL not in jurnal.xato_matni
    assert LOGIN not in jurnal.xato_matni


def _boshqa_ulanish():
    s = connection.settings_dict
    return psycopg.connect(
        dbname=s["NAME"], user=s["USER"], password=s["PASSWORD"],
        host=s["HOST"] or None, port=s["PORT"] or None, autocommit=True,
    )


def test_band_bolsa():
    client = SoxtaClient()
    with _boshqa_ulanish() as boshqa:
        boshqa.execute("SELECT pg_advisory_lock(%s)", [QULF])
        try:
            with pytest.raises(SinxronBand):
                sinxronla(client, hozir=HOZIR)
        finally:
            boshqa.execute("SELECT pg_advisory_unlock(%s)", [QULF])

    jurnal = SinxronJurnal.objects.order_by("-boshlandi", "-id").first()
    assert jurnal.natija == SinxronJurnal.Natija.BAND
    assert AV.objects.count() == 0


def test_qulf_bushatiladi():
    client = SoxtaClient()
    sinxronla(client, hozir=HOZIR)
    client.vositalar_xatosi = OneCXato("ulanmadi")
    sinxronla(client, hozir=HOZIR)

    with _boshqa_ulanish() as boshqa:
        olindi = boshqa.execute("SELECT pg_try_advisory_lock(%s)", [QULF]).fetchone()[0]
        boshqa.execute("SELECT pg_advisory_unlock_all()")

    assert olindi is True


def test_bosh_reflar_null():
    client = SoxtaClient()
    vositalar = client.vos["vositalar"]
    vositalar[0]["turi"] = None
    vositalar[0]["filial"] = None
    vositalar[1]["turi"] = str(uuid.uuid4())  # spravochnikda yo'q
    vositalar[1]["tashkilot"] = str(uuid.uuid4())
    client.sprav["xodimlar"][0]["filial"] = None
    client.sprav["xodimlar"][1]["filial"] = str(uuid.uuid4())
    client.vos["qoldiqlar"][0]["filial"] = None
    client.vos["qoldiqlar"][1]["av"] = str(uuid.uuid4())
    client.har[0]["hujjat_ref"] = None
    client.har[1]["av"] = str(uuid.uuid4())
    client.har[2]["sana"] = None

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.OK, jurnal.xato_matni
    av0 = AV.objects.get(ref_1c=vositalar[0]["ref"])
    assert av0.turi is None and av0.filial_rekvizit is None
    av1 = AV.objects.get(ref_1c=vositalar[1]["ref"])
    assert av1.turi is None and av1.tashkilot is None
    assert Xodim.objects.get(ref_1c=client.sprav["xodimlar"][0]["ref"]).filial is None
    assert Xodim.objects.get(ref_1c=client.sprav["xodimlar"][1]["ref"]).filial is None
    assert AVQoldiq.objects.count() == len(yaroqli_qoldiqlar(client))
    assert jurnal.ozgarishlar["qoldiq_otkazildi"] == len(client.vos["qoldiqlar"]) - len(yaroqli_qoldiqlar(client))
    assert Harakat1C.objects.count() == len(yaroqli_harakatlar(client))
    assert jurnal.ozgarishlar["harakat_otkazildi"] == len(client.har) - len(yaroqli_harakatlar(client))


def test_ketma_ket_xatolar():
    client = SoxtaClient()
    client.vositalar_xatosi = OneCXato("ulanmadi")
    for _ in range(3):
        sinxronla(client, hozir=HOZIR)

    assert ketma_ket_xatolar() == 3
    assert oxirgi_muvaffaqiyatli() is None

    client.vositalar_xatosi = None
    ok = sinxronla(client, hozir=HOZIR)

    assert ketma_ket_xatolar() == 0
    assert oxirgi_muvaffaqiyatli() == ok


@pytest.fixture
def buyruq_client(monkeypatch):
    client = SoxtaClient()
    monkeypatch.setattr("onec.management.commands.sinxron.OneCClient.settingsdan", lambda: client)
    return client


def test_buyruq_ok(buyruq_client, capsys):
    call_command("sinxron", "--toliq")

    jurnal = SinxronJurnal.objects.get()
    assert jurnal.natija == SinxronJurnal.Natija.OK and jurnal.toliq is True
    assert "muvaffaqiyatli" in capsys.readouterr().out


def test_buyruq_xato(buyruq_client):
    buyruq_client.vositalar_xatosi = OneCXato("ulanmadi")

    with pytest.raises(CommandError) as xato:
        call_command("sinxron")

    assert xato.value.returncode == 1
    assert "ulanmadi" in str(xato.value)


def test_buyruq_band(buyruq_client, capsys):
    with _boshqa_ulanish() as boshqa:
        boshqa.execute("SELECT pg_advisory_lock(%s)", [QULF])
        try:
            call_command("sinxron")
        finally:
            boshqa.execute("SELECT pg_advisory_unlock(%s)", [QULF])

    assert "band" in capsys.readouterr().out.lower()


def test_birinchi_inkremental_chaqiriq_toliq_bajariladi():
    client = SoxtaClient()

    jurnal = sinxronla(client, toliq=False, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.OK and jurnal.toliq is True
    dan, _ = client.harakat_sorovlari[-1]
    assert dan.year <= 1900


def test_toliq_muvaffaqiyatsiz_bolsa_keyingisi_ham_toliq():
    client = SoxtaClient()
    client.vositalar_xatosi = OneCXato("1C HTTP 500 qaytardi: /vositalar")
    assert sinxronla(client, hozir=HOZIR).natija == SinxronJurnal.Natija.XATO
    client.vositalar_xatosi = None

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.natija == SinxronJurnal.Natija.OK and jurnal.toliq is True


def test_toliq_sinxrondan_keyin_inkremental_qoladi():
    client = SoxtaClient()
    sinxronla(client, toliq=True, hozir=HOZIR)

    jurnal = sinxronla(client, hozir=HOZIR)

    assert jurnal.toliq is False
    dan, _ = client.harakat_sorovlari[-1]
    assert dan == (HOZIR - timedelta(days=45)).replace(tzinfo=None)


def _band_keyin_ok(monkeypatch, band_soni):
    """`sinxronla` avval `band_soni` marta band, keyin haqiqiy natija; `sleep` chaqiruvlari yoziladi."""
    import onec.management.commands.sinxron as buyruq

    asl = buyruq.sinxronla
    holat = {"chaqiruv": 0}
    kutishlar = []

    def soxta(client, toliq=False):
        holat["chaqiruv"] += 1
        if holat["chaqiruv"] <= band_soni:
            raise SinxronBand("band")
        return asl(client, toliq=toliq, hozir=HOZIR)

    monkeypatch.setattr(buyruq, "sinxronla", soxta)
    monkeypatch.setattr(buyruq.time, "sleep", kutishlar.append)
    return holat, kutishlar


def test_buyruq_toliq_band_bolsa_qayta_urinadi(buyruq_client, monkeypatch, capsys):
    holat, kutishlar = _band_keyin_ok(monkeypatch, 3)

    call_command("sinxron", "--toliq")

    assert holat["chaqiruv"] == 4
    assert kutishlar == [15, 15, 15]
    assert SinxronJurnal.objects.get().toliq is True
    assert "muvaffaqiyatli" in capsys.readouterr().out


def test_buyruq_toliq_5_daqiqadan_keyin_toxtaydi(buyruq_client, monkeypatch, capsys):
    holat, kutishlar = _band_keyin_ok(monkeypatch, 10_000)

    call_command("sinxron", "--toliq")

    assert sum(kutishlar) == 300 and set(kutishlar) == {15}
    assert holat["chaqiruv"] == 21
    assert "o'tkazib yuborildi" in capsys.readouterr().out
    assert not SinxronJurnal.objects.exists()


def test_buyruq_inkremental_band_kutmaydi(buyruq_client, monkeypatch, capsys):
    holat, kutishlar = _band_keyin_ok(monkeypatch, 1)

    call_command("sinxron")

    assert holat["chaqiruv"] == 1 and kutishlar == []
    assert "o'tkazib yuborildi" in capsys.readouterr().out
