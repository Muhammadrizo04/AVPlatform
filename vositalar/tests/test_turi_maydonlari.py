"""Mahalliy sozlangan AV turi maydonlarini ishchi bazaga o'tkazish buyrug'i."""
import json
import uuid
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from jurnal.models import Jurnal
from onec.models import AVTuri
from panel.sozlamalar import MAYDON_TIPLARI
from vositalar.models import AVTuriSozlama

pytestmark = pytest.mark.django_db

CPU = {"kalit": "cpu", "nomi": "CPU", "tip": "tanlov", "majburiy": False, "tanlov_qiymatlari": ["i5", "i7"]}
RAM = {"kalit": "ram", "nomi": "RAM", "tip": "matn", "majburiy": False, "tanlov_qiymatlari": []}


def tur_yarat(nomi="KOMPYUTERLAR"):
    return AVTuri.objects.create(ref_1c=uuid.uuid4(), nomi=nomi)


def yukla(tmp_path, *turlar):
    fayl = tmp_path / "t.json"
    fayl.write_text(json.dumps(list(turlar), ensure_ascii=False), encoding="utf8")
    chiqish = StringIO()
    call_command("turi_maydonlarini_yukla", str(fayl), stdout=chiqish)
    return chiqish.getvalue()


def yozuv(tur, *maydonlar, ref=None):
    return {"ref_1c": str(ref or tur.ref_1c), "nomi": tur.nomi, "maydonlar": list(maydonlar)}


def maydonlar(tur):
    return AVTuriSozlama.objects.get(av_turi=tur).maydonlar


def test_ref_boyicha_yuklaydi(tmp_path):
    tur = tur_yarat()

    natija = yukla(tmp_path, yozuv(tur, CPU, RAM))

    assert maydonlar(tur) == [CPU, RAM] and "2 ta maydon" in natija


def test_ref_topilmasa_yagona_nom_boyicha(tmp_path):
    tur = tur_yarat()

    yukla(tmp_path, yozuv(tur, CPU, ref=uuid.uuid4()))

    assert maydonlar(tur) == [CPU]


def test_nom_takrorlansa_taxmin_qilmaydi(tmp_path):
    a, b = tur_yarat(), tur_yarat()

    natija = yukla(tmp_path, yozuv(a, CPU, ref=uuid.uuid4()))

    assert "topilmadi" in natija
    assert not AVTuriSozlama.objects.filter(av_turi__in=[a, b]).exists()


def test_mavjud_maydon_va_muddat_saqlanadi(tmp_path):
    tur = tur_yarat()
    ozgacha = {**CPU, "nomi": "Mening nomim"}
    AVTuriSozlama.objects.create(av_turi=tur, maydonlar=[ozgacha], xizmat_muddati_oy=24)

    yukla(tmp_path, yozuv(tur, CPU, RAM))

    s = AVTuriSozlama.objects.get(av_turi=tur)
    assert s.maydonlar == [ozgacha, RAM] and s.xizmat_muddati_oy == 24


def test_qayta_ishga_tushirish_hech_narsa_ozgartirmaydi(tmp_path):
    tur = tur_yarat()
    yukla(tmp_path, yozuv(tur, CPU))
    oldin = Jurnal.objects.count()

    natija = yukla(tmp_path, yozuv(tur, CPU))

    assert maydonlar(tur) == [CPU] and Jurnal.objects.count() == oldin and "allaqachon bor" in natija


def test_jurnalda_buyruq_nomi_sinxron_emas(tmp_path):
    yukla(tmp_path, yozuv(tur_yarat(), CPU))

    assert Jurnal.objects.get(maydon="maydonlar").kim_nomi == "Buyruq: turi_maydonlarini_yukla"


def test_deploy_fayli_togri():
    turlar = json.loads((Path(settings.BASE_DIR) / "deploy" / "turi_maydonlari.json").read_text(encoding="utf8"))

    kompyuter = next(t for t in turlar if t["nomi"] == "KOMPYUTERLAR")
    assert uuid.UUID(kompyuter["ref_1c"]) and len(kompyuter["maydonlar"]) == 9
    assert all(m["tip"] in MAYDON_TIPLARI and m["kalit"] and m["nomi"] for m in kompyuter["maydonlar"])
