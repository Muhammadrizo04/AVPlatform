"""Reviziya servisi: ochish (surat), qayd qo'shish/tuzatish, yakunlash va bekor qilish (spec §2, §3.1, §4).

Holat o'tishlari va qaydlar reviziya qatorini `select_for_update` bilan qulflab bajariladi: yakunlash bilan parallel
kelgan qayd yopiq reviziyaga tushmaydi, ikki revizorning bir vaqtdagi skanlari bitta qaydga qo'shiladi.
"""
from decimal import Decimal

from django.db import connection, transaction
from django.db.models import Max, Sum
from django.db.models.functions import Trim
from django.utils import timezone

from hisoblar.huquqlar import huquqi_bor
from onec.models import AV, AVQoldiq, Filial
from vositalar.bolimlar import pastkilar
from vositalar.models import Holat as TaqsimotHolat
from vositalar.models import Taqsimot
from vositalar.rasmlar import rasm_saqla

from .models import Reviziya, ReviziyaKutilgan, ReviziyaQayd, XodimLavozimi

NOL = Decimal("0")
MAKS_SONI = Decimal("1000000000000")  # DecimalField(max_digits=15, decimal_places=3) chegarasi
RV_RAQAM_QULFI = 7310003  # reviziya raqami va qamrov tekshiruvi uchun advisory lock (sinxron 7310001, akt 7310002)
NOMALUM = "noma'lum"
BOSHQA_FILIAL = "boshqa filial"
KOMISSIYA_RAIS, KOMISSIYA_AZO = "rais", "azo"
KOMISSIYA_ROLLARI = ((KOMISSIYA_RAIS, "Rais"), (KOMISSIYA_AZO, "A'zo"))
_HAMMASI = object()  # progress(): «barcha bo'limlar» belgisi (None — bo'limsiz)


class ReviziyaXato(Exception):
    """Reviziya amalini bajarib bo'lmaydi; matni foydalanuvchiga ko'rsatiladi."""


def _qamrov(bolim) -> set[int] | None:
    return None if bolim is None else {bolim.pk, *(b.pk for b in pastkilar(bolim))}


def qamrov_bolim_idlari(reviziya: Reviziya) -> set[int] | None:
    """Reviziya qamrovidagi bo'lim pk'lari (tanlangan bo'lim va ichki bo'limlari); None — butun filial."""
    return _qamrov(reviziya.bolim)


def _ota_idlari(bolim) -> set[int]:
    natija, joriy = set(), bolim.ota
    while joriy is not None:
        natija.add(joriy.pk)
        joriy = joriy.ota
    return natija


def _kesishadi(filial, bolim) -> bool:
    """Shu filialda qamrovi `bolim` bilan kesishgan ochiq reviziya bormi."""
    ochiqlar = list(
        Reviziya.objects.filter(filial=filial, holat=Reviziya.Holat.OCHIQ).values_list("bolim_id", flat=True)
    )
    if not ochiqlar:
        return False
    if bolim is None or None in ochiqlar:
        return True
    yaqinlar = _qamrov(bolim) | _ota_idlari(bolim)
    return any(b in yaqinlar for b in ochiqlar)


def _komissiya(komissiya) -> list[dict]:
    """A'zolar ro'yxatini tozalaydi: bo'sh ism tashlanadi, bitta xodim bir marta, rais bittadan ko'p emas va birinchi.
    Element: `{"xodim_id": int | None, "ism", "lavozim", "rol": "rais" | "azo"}` (xodim_id yo'q — 1C'da yo'q odam)."""
    natija, korilgan = [], set()
    for azo in komissiya or []:
        ism = str(azo.get("ism") or "").strip()
        xodim_id = azo.get("xodim_id") or None
        if not ism or (xodim_id is not None and xodim_id in korilgan):
            continue
        korilgan.add(xodim_id)
        rol = KOMISSIYA_RAIS if azo.get("rol") == KOMISSIYA_RAIS else KOMISSIYA_AZO
        natija.append({"xodim_id": xodim_id, "ism": ism, "lavozim": str(azo.get("lavozim") or "").strip(), "rol": rol})
    if sum(a["rol"] == KOMISSIYA_RAIS for a in natija) > 1:
        raise ReviziyaXato("Komissiya raisi bitta bo'lishi kerak.")
    return sorted(natija, key=lambda a: a["rol"] != KOMISSIYA_RAIS)


def _lavozimlarni_eslab_qol(komissiya: list[dict]) -> None:
    for a in komissiya:
        if a["xodim_id"] is not None and a["lavozim"]:
            XodimLavozimi.objects.update_or_create(xodim_id=a["xodim_id"], defaults={"lavozim": a["lavozim"]})


def reviziya_och(filial, bolim, revizorlar, komissiya, kim, izoh: str = "") -> Reviziya:
    """Yangi ochiq reviziya: raqam, qamrov kesishmasi tekshiruvi va qamrovdagi faol AV taqsimotidan surat."""
    if bolim is not None and bolim.filial_id != filial.pk:
        raise ReviziyaXato("Bo'lim tanlangan filialga tegishli emas.")
    revizorlar = list(revizorlar)
    if not revizorlar:
        raise ReviziyaXato("Kamida bitta revizor tanlang.")
    komissiya = _komissiya(komissiya)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [RV_RAQAM_QULFI])
        if _kesishadi(filial, bolim):
            raise ReviziyaXato("Bu filial yoki bo'lim bo'yicha qamrovi kesishgan ochiq reviziya bor.")
        oxirgi = Reviziya.objects.aggregate(m=Max("raqam"))["m"]
        reviziya = Reviziya.objects.create(
            raqam=1 if oxirgi is None else oxirgi + 1,
            filial=filial,
            bolim=bolim,
            komissiya=komissiya,
            izoh=izoh,
            ochdi=kim,
        )
        reviziya.revizorlar.set(revizorlar)
        _lavozimlarni_eslab_qol(komissiya)
        qatorlar = Taqsimot.objects.filter(filial=filial, av_id__in=AV.objects.faol().values("pk"))
        qamrov = _qamrov(bolim)
        if qamrov is not None:
            qatorlar = qatorlar.filter(bolim_id__in=qamrov)
        ReviziyaKutilgan.objects.bulk_create(
            ReviziyaKutilgan(
                reviziya=reviziya, av_id=t.av_id, bolim_id=t.bolim_id, mol_id=t.mol_id, holat=t.holat,
                soni=t.soni, taqsimot_id=t.pk,
            )
            for t in qatorlar.order_by("pk")
        )
    return reviziya


def qr_tahlil(matn: str, reviziya: Reviziya) -> tuple[AV | None, str]:
    """`DS|<filial kodi>|<inv>` -> (AV, ""), yoki (None, "noma'lum" | "boshqa filial"). Arxiv AV ham qaytadi.
    NUL bayt bor matn — noma'lum (PostgreSQL matn maydonlari NUL'ni qabul qilmaydi)."""
    if "\x00" in (matn or ""):
        return None, NOMALUM
    qismlar = [q.strip() for q in (matn or "").strip().split("|")]
    if len(qismlar) != 3 or qismlar[0] != "DS" or not qismlar[1] or not qismlar[2]:
        return None, NOMALUM
    _, kod, inv = qismlar
    filial = reviziya.filial
    if kod != filial.kod.strip():
        boshqa = Filial.objects.annotate(k=Trim("kod")).filter(k=kod).exclude(pk=filial.pk).exists()
        return None, BOSHQA_FILIAL if boshqa else NOMALUM
    nomzodlar = list(
        AV.objects.annotate(inv=Trim("inv_raqam")).filter(filial_rekvizit=filial, inv=inv).order_by("pk")
    )
    if not nomzodlar:
        return None, NOMALUM
    if len(nomzodlar) > 1:
        shu_yerda = set(
            AVQoldiq.objects.filter(av__in=nomzodlar, filial=filial, soni__gt=0).values_list("av_id", flat=True)
        )
        for av in nomzodlar:
            if av.pk in shu_yerda:
                return av, ""
    return nomzodlar[0], ""


def _soni_tekshir(soni, *, nol_mumkin: bool) -> Decimal:
    try:
        soni = soni if isinstance(soni, Decimal) else Decimal(str(soni))
    except ArithmeticError:
        raise ReviziyaXato("Sonni to'g'ri kiriting.") from None
    if not soni.is_finite() or soni < 0 or (soni == 0 and not nol_mumkin):
        raise ReviziyaXato("Son noldan katta bo'lishi kerak." if not nol_mumkin else "Son manfiy bo'lmasin.")
    if soni >= MAKS_SONI or soni != soni.quantize(Decimal("0.001")):
        raise ReviziyaXato("Sonni to'g'ri kiriting.")
    return soni


def standart_holat(reviziya: Reviziya, av, bolim_id) -> str:
    """Skanerlangan AV uchun oldindan tanlanadigan holat: shu xonadagi kutilgan holat, aks holda suratdagi istalgan
    xonadagi kutilgan holat (eng kichik pk), aks holda «ishlatilmoqda». Skanerlangan AV topilgan — «topilmadi»
    holati «ishlatilmoqda» ga almashadi."""
    holat = None
    if av is not None:
        kutilganlar = reviziya.kutilganlar.filter(av=av).order_by("pk")
        holat = kutilganlar.filter(bolim_id=bolim_id).values_list("holat", flat=True).first()
        if holat is None:
            holat = kutilganlar.values_list("holat", flat=True).first()
    if not holat or holat == TaqsimotHolat.TOPILMADI:
        return TaqsimotHolat.ISHLATILMOQDA
    return holat


def _ochiq_qulfla(reviziya_id: int) -> Reviziya:
    reviziya = Reviziya.objects.select_for_update().get(pk=reviziya_id)
    if reviziya.holat != Reviziya.Holat.OCHIQ:
        raise ReviziyaXato("Reviziya ochiq emas.")
    return reviziya


def qayd_qosh(
    reviziya, bolim, kim, *, av=None, qr_matn="", soni=Decimal("1"), holat=None, usul="qr", izoh="", rasm_fayl=None
) -> ReviziyaQayd:
    """Qayd qo'shadi; (bo'lim, AV, holat) yoki noma'lum QR matni bo'yicha mavjud bo'lsa — soni qo'shiladi.
    Huquqni chaqiruvchi tekshiradi; bu yerda — holat, qamrov va son."""
    soni = _soni_tekshir(soni, nol_mumkin=False)
    qr_matn = "" if av is not None else (qr_matn or "").strip()
    if av is None and not qr_matn:
        raise ReviziyaXato("AV yoki QR matni kerak.")
    if usul not in ReviziyaQayd.Usul.values:
        raise ReviziyaXato("Noto'g'ri usul.")
    if holat is not None and holat not in TaqsimotHolat.values:
        raise ReviziyaXato("Noto'g'ri holat.")
    with transaction.atomic():
        reviziya = _ochiq_qulfla(reviziya.pk)
        if bolim is not None:
            qamrov = qamrov_bolim_idlari(reviziya)
            if bolim.filial_id != reviziya.filial_id or (qamrov is not None and bolim.pk not in qamrov):
                raise ReviziyaXato("Bo'lim reviziya qamrovida emas.")
        bolim_id = None if bolim is None else bolim.pk
        if holat is None:
            holat = standart_holat(reviziya, av, bolim_id)
        qayd = (
            ReviziyaQayd.objects.select_for_update()
            .filter(reviziya=reviziya, bolim_id=bolim_id, av=av, holat=holat, qr_matn=qr_matn)
            .first()
        )
        if qayd is not None and qayd.soni + soni >= MAKS_SONI:
            raise ReviziyaXato("Son juda katta.")
        # Rasm oxirida saqlanadi; keyingi xatoda fayllar o'chiriladi (tranzaksiya bekor bo'lsa ham fayl qolmasin)
        rasm = rasm_saqla(av, rasm_fayl, kim) if rasm_fayl is not None and av is not None else None
        try:
            if qayd is None:
                return ReviziyaQayd.objects.create(
                    reviziya=reviziya, bolim_id=bolim_id, av=av, qr_matn=qr_matn, soni=soni, holat=holat,
                    usul=usul, izoh=izoh, rasm=rasm, kim=kim,
                )
            qayd.soni += soni
            if izoh:
                qayd.izoh = izoh
            if rasm is not None:
                qayd.rasm = rasm
            qayd.save()
            return qayd
        except BaseException:
            if rasm is not None:
                _rasm_fayllarini_ochir(rasm)
            raise


def _rasm_fayllarini_ochir(rasm) -> None:
    for maydon in (rasm.fayl, rasm.miniatyura):
        if maydon:
            maydon.delete(save=False)


def qayd_tuzat(qayd: ReviziyaQayd, soni, kim) -> ReviziyaQayd | None:
    """Qayd sonini qo'lda o'rnatadi; 0 — qayd o'chiriladi (None). Faqat o'z qaydi yoki `reviziya_boshqarish`."""
    soni = _soni_tekshir(soni, nol_mumkin=True)
    with transaction.atomic():
        _ochiq_qulfla(qayd.reviziya_id)
        qayd = ReviziyaQayd.objects.select_for_update().filter(pk=qayd.pk).first()
        if qayd is None:
            raise ReviziyaXato("Qayd topilmadi.")
        if qayd.kim_id != kim.pk and not huquqi_bor(kim, "reviziya_boshqarish"):
            raise ReviziyaXato("Faqat o'z qaydingizni tuzatishingiz mumkin.")
        if soni == 0:
            qayd.delete()
            return None
        qayd.soni = soni
        qayd.save(update_fields=["soni", "yangilangan"])
        return qayd


def revizorlarni_ozgartir(reviziya: Reviziya, revizorlar, kim) -> None:
    """Ochiq reviziya revizorlarini almashtiradi. Olib tashlangan revizorning qaydlari saqlanadi, lekin u endi
    skanerlay olmaydi (mobil ruxsat `revizorlar` ro'yxatidan)."""
    revizorlar = list(revizorlar)
    if not revizorlar:
        raise ReviziyaXato("Kamida bitta revizor tanlang.")
    with transaction.atomic():
        reviziya = _ochiq_qulfla(reviziya.pk)
        reviziya.revizorlar.set(revizorlar)


def yakunla(reviziya: Reviziya, kim) -> None:
    """Ochiq reviziyani yakunlaydi: qaydlar yopiladi."""
    with transaction.atomic():
        reviziya = _ochiq_qulfla(reviziya.pk)
        reviziya.holat = Reviziya.Holat.YAKUNLANGAN
        reviziya.yakunladi = kim
        reviziya.yakunlangan_vaqt = timezone.now()
        reviziya.save(update_fields=["holat", "yakunladi", "yakunlangan_vaqt"])


def bekor_qil(reviziya: Reviziya, kim) -> None:
    """Ochiq reviziyani bekor qiladi; qaydlar saqlanadi, taqsimotga ta'sir yo'q."""
    with transaction.atomic():
        reviziya = _ochiq_qulfla(reviziya.pk)
        reviziya.holat = Reviziya.Holat.BEKOR
        reviziya.bekor_qildi = kim
        reviziya.bekor_vaqti = timezone.now()
        reviziya.save(update_fields=["holat", "bekor_qildi", "bekor_vaqti"])


def progress(reviziya: Reviziya, bolim_id=_HAMMASI) -> tuple[Decimal, Decimal]:
    """(belgilangan, kutilgan) dona. `bolim_id` berilmasa — butun reviziya; None — bo'limsiz."""
    qaydlar = reviziya.qaydlar.filter(av__isnull=False)
    kutilganlar = reviziya.kutilganlar.all()
    if bolim_id is not _HAMMASI:
        qaydlar = qaydlar.filter(bolim_id=bolim_id)
        kutilganlar = kutilganlar.filter(bolim_id=bolim_id)
    belgilangan = qaydlar.aggregate(s=Sum("soni"))["s"] or NOL
    kutilgan = kutilganlar.aggregate(s=Sum("soni"))["s"] or NOL
    return belgilangan, kutilgan
