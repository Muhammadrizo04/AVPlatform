from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from reviziya.models import Reviziya, ReviziyaQayd
from reviziya.servis import (
    ReviziyaXato,
    bekor_qil,
    progress,
    qamrov_bolim_idlari,
    qayd_qosh,
    qayd_tuzat,
    qr_tahlil,
    reviziya_och,
    standart_holat,
    yakunla,
)
from vositalar.models import Bolim, Holat, Rasm
from vositalar.tests.test_bayroqlar import av_yarat, qator
from vositalar.tests.test_kartochka import rasm_baytlari, yuklama


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def filial(filial_yarat):
    return filial_yarat("07")


@pytest.fixture
def hisobchi(foydalanuvchi):
    return foydalanuvchi("hisobchi")


@pytest.fixture
def revizor(foydalanuvchi):
    return foydalanuvchi("revizor")


@pytest.fixture
def och(hisobchi, revizor):
    def yarat(filial, bolim=None, **kw):
        return reviziya_och(filial, bolim, [revizor], [{"ism": "Ali", "lavozim": "Rais"}], hisobchi, **kw)

    return yarat


def test_ochish_surat_filial(filial, och, filial_yarat):
    ombor = Bolim.objects.create(filial=filial, nomi="Ombor")
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    stol = av_yarat(filial, inv="1", soni="3")
    q1 = qator(stol, filial, "2", bolim=ombor)
    q2 = qator(stol, filial, "1", bolim=zal)
    q2.holat = Holat.TAMIRDA
    q2.save()
    stul = av_yarat(filial, inv="2")
    qator(stul, filial, "1")
    arxiv = av_yarat(filial, inv="3", soni="0")
    qator(arxiv, filial, "1", bolim=zal)
    boshqa = filial_yarat("08")
    begona = av_yarat(boshqa, inv="1")
    qator(begona, boshqa, "1")

    rv = och(filial, izoh="Yillik")

    assert rv.raqam == 1 and rv.holat == Reviziya.Holat.OCHIQ and rv.izoh == "Yillik"
    assert list(rv.revizorlar.all())
    assert rv.komissiya == [{"xodim_id": None, "ism": "Ali", "lavozim": "Rais", "rol": "azo"}]
    assert rv.kutilganlar.count() == 3
    k1 = rv.kutilganlar.get(taqsimot_id=q1.pk)
    assert (k1.av_id, k1.bolim_id, k1.soni, k1.holat) == (stol.pk, ombor.pk, Decimal("2"), Holat.ISHLATILMOQDA)
    assert rv.kutilganlar.get(taqsimot_id=q2.pk).holat == Holat.TAMIRDA
    assert not rv.kutilganlar.filter(av=arxiv).exists()
    assert qamrov_bolim_idlari(rv) is None


def test_ochish_surat_bolim_ichki_bilan(filial, och):
    ota = Bolim.objects.create(filial=filial, nomi="Bino")
    ichki = Bolim.objects.create(filial=filial, ota=ota, nomi="Xona")
    chuqur = Bolim.objects.create(filial=filial, ota=ichki, nomi="Shkaf")
    boshqa = Bolim.objects.create(filial=filial, nomi="Ombor")
    av = av_yarat(filial, soni="5")
    qator(av, filial, "1", bolim=ota)
    qator(av, filial, "1", bolim=ichki)
    qator(av, filial, "1", bolim=chuqur)
    qator(av, filial, "1", bolim=boshqa)
    qator(av, filial, "1")

    rv = och(filial, ota)

    assert set(rv.kutilganlar.values_list("bolim_id", flat=True)) == {ota.pk, ichki.pk, chuqur.pk}
    assert qamrov_bolim_idlari(rv) == {ota.pk, ichki.pk, chuqur.pk}


def test_ochish_boshqa_filial_bolimi(filial, och, filial_yarat):
    begona = Bolim.objects.create(filial=filial_yarat("08"), nomi="Zal")
    with pytest.raises(ReviziyaXato):
        och(filial, begona)


def test_qamrov_kesishmasi(filial, och, filial_yarat):
    ota = Bolim.objects.create(filial=filial, nomi="Bino")
    ichki = Bolim.objects.create(filial=filial, ota=ota, nomi="Xona")
    qoshni = Bolim.objects.create(filial=filial, nomi="Ombor")

    butun = och(filial)
    with pytest.raises(ReviziyaXato):
        och(filial, ichki)
    with pytest.raises(ReviziyaXato):
        och(filial)
    och(filial_yarat("08"))  # boshqa filial — mumkin

    bekor_qil(butun, butun.ochdi)
    och(filial, ichki)  # avvalgisi bekor — mumkin
    with pytest.raises(ReviziyaXato):
        och(filial, ota)  # ota <- ichki
    with pytest.raises(ReviziyaXato):
        och(filial, ichki)
    with pytest.raises(ReviziyaXato):
        och(filial)
    och(filial, qoshni)  # kesishmaydi

    assert Reviziya.objects.filter(holat=Reviziya.Holat.OCHIQ).count() == 3


def test_qamrov_kesishmasi_ichki_ochiq_ota_bilan(filial, och):
    ota = Bolim.objects.create(filial=filial, nomi="Bino")
    ichki = Bolim.objects.create(filial=filial, ota=ota, nomi="Xona")
    och(filial, ota)
    with pytest.raises(ReviziyaXato):
        och(filial, ichki)  # ichki -> ota


def test_raqam_ketma_ket(filial, och, filial_yarat):
    assert och(filial).raqam == 1
    assert och(filial_yarat("08")).raqam == 2


def test_takror_skan_bitta_qayd(filial, och, revizor, hisobchi):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    av = av_yarat(filial, soni="3")
    t = qator(av, filial, "3", bolim=zal)
    t.holat = Holat.ZAXIRADA
    t.save()
    rv = och(filial)

    birinchi = qayd_qosh(rv, zal, revizor, av=av)
    ikkinchi = qayd_qosh(rv, zal, hisobchi, av=av, usul="qidiruv")

    assert ikkinchi.pk == birinchi.pk
    assert rv.qaydlar.count() == 1
    qayd = rv.qaydlar.get()
    assert qayd.soni == Decimal("2") and qayd.holat == Holat.ZAXIRADA and qayd.kim == revizor
    # kutilgan qatori bo'lmagan joyda — suratdagi boshqa xona holati (I-2); suratda yo'q AV — ishlatilmoqda
    assert qayd_qosh(rv, None, revizor, av=av).holat == Holat.ZAXIRADA
    assert qayd_qosh(rv, None, revizor, av=av_yarat(filial, inv="YANGI")).holat == Holat.ISHLATILMOQDA


def test_qayd_notogri_soni(filial, och, revizor):
    av = av_yarat(filial)
    rv = och(filial)
    for soni in (Decimal("0"), Decimal("-1"), Decimal("NaN")):
        with pytest.raises(ReviziyaXato):
            qayd_qosh(rv, None, revizor, av=av, soni=soni)


def test_qayd_qamrovdan_tashqari_bolim(filial, och, revizor, filial_yarat):
    ota = Bolim.objects.create(filial=filial, nomi="Bino")
    qoshni = Bolim.objects.create(filial=filial, nomi="Ombor")
    av = av_yarat(filial)
    rv = och(filial, ota)
    with pytest.raises(ReviziyaXato):
        qayd_qosh(rv, qoshni, revizor, av=av)
    with pytest.raises(ReviziyaXato):
        qayd_qosh(rv, Bolim.objects.create(filial=filial_yarat("08"), nomi="Zal"), revizor, av=av)
    assert qayd_qosh(rv, None, revizor, av=av).bolim is None  # bo'limsiz — mumkin


def test_qr_tahlil(filial, och, revizor, filial_yarat):
    filial_yarat("08")
    av = av_yarat(filial, inv="INV-1")
    arxiv = av_yarat(filial, inv="ARX", soni="0")
    rv = och(filial)

    assert qr_tahlil("DS|07|INV-1", rv) == (av, "")
    assert qr_tahlil("  DS|07|INV-1 \n", rv) == (av, "")
    assert qr_tahlil("DS|07|ARX", rv) == (arxiv, "")
    assert qr_tahlil("abc", rv) == (None, "noma'lum")
    assert qr_tahlil("DS|99|X", rv) == (None, "noma'lum")
    assert qr_tahlil("DS|07|YOQ", rv) == (None, "noma'lum")
    assert qr_tahlil("DS|08|INV-1", rv) == (None, "boshqa filial")

    qayd = qayd_qosh(rv, None, revizor, qr_matn="abc")
    qayd_qosh(rv, None, revizor, qr_matn="abc")
    qayd.refresh_from_db()
    assert qayd.av is None and qayd.qr_matn == "abc" and qayd.soni == Decimal("2")


def test_qr_tahlil_takror_inv(filial, och, filial_yarat):
    ketgan = av_yarat(filial, inv="5", qoldiq_filial=filial_yarat("08"))
    shu_yerda = av_yarat(filial, inv="5")
    rv = och(filial)
    assert ketgan.pk < shu_yerda.pk
    assert qr_tahlil("DS|07|5", rv) == (shu_yerda, "")


def test_qayd_avsiz_qrsiz_xato(filial, och, revizor):
    rv = och(filial)
    with pytest.raises(ReviziyaXato):
        qayd_qosh(rv, None, revizor)


def test_qayd_rasm(filial, och, revizor):
    av = av_yarat(filial)
    rv = och(filial)
    qayd = qayd_qosh(rv, None, revizor, av=av, rasm_fayl=yuklama(rasm_baytlari()), izoh="Singan")
    assert qayd.rasm is not None and qayd.rasm.av == av and qayd.izoh == "Singan"
    with pytest.raises(ValidationError):
        qayd_qosh(rv, None, revizor, av=av, rasm_fayl=yuklama(b"rasm emas"))
    qayd.refresh_from_db()
    assert qayd.soni == Decimal("1")  # xato bo'lgan urinish soni qo'shmadi


def test_yopiq_reviziyaga_qayd_yoq(filial, och, revizor, hisobchi):
    av = av_yarat(filial)
    rv = och(filial)
    qayd = qayd_qosh(rv, None, revizor, av=av)
    yakunla(rv, hisobchi)
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.YAKUNLANGAN and rv.yakunladi == hisobchi and rv.yakunlangan_vaqt
    with pytest.raises(ReviziyaXato):
        qayd_qosh(rv, None, revizor, av=av)
    with pytest.raises(ReviziyaXato):
        qayd_tuzat(qayd, Decimal("3"), revizor)
    with pytest.raises(ReviziyaXato):
        yakunla(rv, hisobchi)


def test_qayd_tuzat_nol_ochiradi(filial, och, revizor):
    av = av_yarat(filial)
    rv = och(filial)
    qayd = qayd_qosh(rv, None, revizor, av=av)
    tuzatilgan = qayd_tuzat(qayd, Decimal("4"), revizor)
    assert tuzatilgan.soni == Decimal("4")
    assert qayd_tuzat(qayd, Decimal("0"), revizor) is None
    assert not ReviziyaQayd.objects.filter(pk=qayd.pk).exists()


def test_qayd_tuzat_manfiy(filial, och, revizor):
    rv = och(filial)
    qayd = qayd_qosh(rv, None, revizor, av=av_yarat(filial))
    with pytest.raises(ReviziyaXato):
        qayd_tuzat(qayd, Decimal("-1"), revizor)


def test_qayd_tuzat_boshqaniki(filial, och, revizor, hisobchi, foydalanuvchi):
    rv = och(filial)
    qayd = qayd_qosh(rv, None, revizor, av=av_yarat(filial))
    with pytest.raises(ReviziyaXato):
        qayd_tuzat(qayd, Decimal("2"), foydalanuvchi("hr"))  # reviziya_boshqarish yo'q
    assert qayd_tuzat(qayd, Decimal("2"), hisobchi).soni == Decimal("2")


def test_bekor_faqat_ochiqdan(filial, och, hisobchi, filial_yarat):
    rv = och(filial)
    bekor_qil(rv, hisobchi)
    rv.refresh_from_db()
    assert rv.holat == Reviziya.Holat.BEKOR and rv.bekor_qildi == hisobchi and rv.bekor_vaqti
    with pytest.raises(ReviziyaXato):
        bekor_qil(rv, hisobchi)
    with pytest.raises(ReviziyaXato):
        yakunla(rv, hisobchi)

    yakunlangan = och(filial_yarat("08"))
    yakunla(yakunlangan, hisobchi)
    with pytest.raises(ReviziyaXato):
        bekor_qil(yakunlangan, hisobchi)


def test_progress(filial, och, revizor):
    zal = Bolim.objects.create(filial=filial, nomi="Zal")
    a = av_yarat(filial, soni="3")
    qator(a, filial, "2", bolim=zal)
    qator(a, filial, "1")
    rv = och(filial)
    qayd_qosh(rv, zal, revizor, av=a)
    qayd_qosh(rv, None, revizor, qr_matn="abc")

    assert progress(rv) == (Decimal("1"), Decimal("3"))
    assert progress(rv, zal.pk) == (Decimal("1"), Decimal("2"))
    assert progress(rv, None) == (Decimal("0"), Decimal("1"))


def test_standart_holat_boshqa_xonada_kutilgan_holat(filial, och, revizor):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    av = av_yarat(filial)
    t = qator(av, filial, "1", bolim=a)
    t.holat = Holat.NOSOZ
    t.save()
    rv = och(filial)

    assert standart_holat(rv, av, b.pk) == Holat.NOSOZ
    qayd = qayd_qosh(rv, b, revizor, av=av)

    assert qayd.holat == Holat.NOSOZ  # boshqa xonada topildi — holati baholanmagan, kutilgani saqlanadi
    assert standart_holat(rv, av_yarat(filial, inv="X"), b.pk) == Holat.ISHLATILMOQDA  # suratda yo'q


def test_standart_holat_shu_xona_ustun_va_topilmadi_ishlatilmoqda(filial, och, revizor):
    a = Bolim.objects.create(filial=filial, nomi="A")
    b = Bolim.objects.create(filial=filial, nomi="B")
    av = av_yarat(filial, soni="2")
    t1 = qator(av, filial, "1", bolim=a)
    t1.holat = Holat.TAMIRDA
    t1.save()
    t2 = qator(av, filial, "1", bolim=b)
    t2.holat = Holat.TOPILMADI
    t2.save()
    rv = och(filial)

    qayd = qayd_qosh(rv, b, revizor, av=av)

    assert qayd.holat == Holat.ISHLATILMOQDA  # shu xonada «topilmadi» edi — skanerlangan AV topilgan
    assert standart_holat(rv, av, a.pk) == Holat.TAMIRDA


def test_qr_tahlil_nul_bayt(filial, och):
    rv = och(filial)
    assert qr_tahlil("DS|" + chr(0) + "|X", rv) == (None, "noma'lum")


def _media_fayllari(settings):
    import os

    return [f for _, _, fayllar in os.walk(settings.MEDIA_ROOT) for f in fayllar]


def test_qayd_rasm_son_oshsa_fayl_saqlanmaydi(filial, och, revizor, settings):
    av = av_yarat(filial)
    rv = och(filial)
    qayd_qosh(rv, None, revizor, av=av, soni=Decimal("999999999999"))

    with pytest.raises(ReviziyaXato, match="Son juda katta"):
        qayd_qosh(rv, None, revizor, av=av, rasm_fayl=yuklama(rasm_baytlari()))

    assert not Rasm.objects.exists() and _media_fayllari(settings) == []


def test_qayd_rasm_keyingi_xatoda_fayllar_ochiriladi(filial, och, revizor, settings, monkeypatch):
    av = av_yarat(filial)
    rv = och(filial)

    def xato(*args, **kwargs):
        raise RuntimeError("baza xatosi")

    monkeypatch.setattr(ReviziyaQayd.objects, "create", xato)
    with pytest.raises(RuntimeError):
        qayd_qosh(rv, None, revizor, av=av, rasm_fayl=yuklama(rasm_baytlari()))

    assert not Rasm.objects.exists() and _media_fayllari(settings) == []
