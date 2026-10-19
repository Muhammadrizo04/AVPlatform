"""Taqsimot amallari: ko'chirish, holat, МОЛ o'zgartirish va 1C kamayganidan keyin kamaytirish (spec §6.3, §8).

Har amal bitta tranzaksiyada: shu (AV, filial) ning taqsimot qatorlari (manba va birlashish nishoni ham ularning
ichida) `select_for_update` bilan pk tartibida qulflanadi (`moslashtir` bilan bir xil tartib — deadlock bo'lmaydi),
son qulflangan qatordan qayta tekshiriladi. Qator bo'linadi, mos qator bo'lsa birlashadi, 0 qolsa o'chiriladi.
Har o'zgarish uchun `TaqsimotHarakat` va Jurnal yoziladi. Xato matnlari foydalanuvchiga ko'rsatiladi (o'zbekcha).
"""
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Sum

from jurnal.yoz import yoz
from onec.models import AVQoldiq

from .models import Holat, Taqsimot, TaqsimotHarakat
from .moslash import _hujjat_izohlari, farq

NOL = Decimal("0")
Sabab = TaqsimotHarakat.Sabab
_SAQLA = object()  # «maydon o'zgarmaydi» belgisi (None — bo'sh bo'lim/МОЛ ma'nosida)


class AmalXato(Exception):
    """Amalni bajarib bo'lmaydi; matni foydalanuvchiga ko'rsatiladi."""


def kochir(qator: Taqsimot, soni: Decimal, bolim, kim) -> Taqsimot:
    """`soni` donani boshqa bo'limga ko'chiradi. Yangi (yoki birlashgan) qatorni qaytaradi."""
    if bolim is None:
        raise AmalXato("Bo'limni tanlang.")
    if bolim.filial_id != qator.filial_id:
        raise AmalXato("Bo'lim boshqa filialga tegishli.")
    if not bolim.faol:
        raise AmalXato("Bo'lim faol emas.")
    return _ozgartir(qator, soni, kim, Sabab.KOCHIRISH, bolim=bolim.pk)


def holat_ozgartir(qator: Taqsimot, soni: Decimal, holat: str, kim) -> Taqsimot:
    """`soni` donaning holatini o'zgartiradi. Yangi (yoki birlashgan) qatorni qaytaradi."""
    if holat not in Holat.values:
        raise AmalXato("Noma'lum holat.")
    return _ozgartir(qator, soni, kim, Sabab.HOLAT, holat=holat)


def mol_ozgartir(qator: Taqsimot, soni: Decimal, mol, kim, hujjat_izoh: str = "") -> Taqsimot:
    """`soni` donaning МОЛ'ini o'zgartiradi (`mol=None` — МОЛ olib tashlanadi). Yangi (yoki birlashgan)
    qatorni qaytaradi. `hujjat_izoh` — masalan, МОЛ akti raqami."""
    return _ozgartir(
        qator, soni, kim, Sabab.MOL_AKT, mol=None if mol is None else mol.pk, hujjat_izoh=hujjat_izoh[:255]
    )


def kamaytir(qator: Taqsimot, soni: Decimal, kim) -> None:
    """1C'da kamaygan, lekin taqsimotda ortiqcha qolgan (farq < 0) `soni` donani qatordan ayiradi."""
    soni = _tekshir_soni(soni, qator.soni)
    with transaction.atomic():
        manba, _ = _qulfla(qator)
        _tekshir_arxiv(manba)
        juft = (manba.av_id, manba.filial_id)
        ortiqcha = -farq(manba.av, manba.filial)
        if ortiqcha <= 0:
            raise AmalXato("Taqsimot 1C qoldig'i bilan mos, kamaytirish shart emas.")
        soni = _tekshir_soni(soni, manba.soni)
        if soni > ortiqcha:
            raise AmalXato(f"Ortiqcha miqdor {ortiqcha:f} dona; undan ko'p kamaytirib bo'lmaydi.")
        jami_oldin = _jami(*juft)
        eski_soni = manba.soni
        _ayir(manba, soni)
        _harakat(
            manba, soni, kim, Sabab.ONEC_KAMAYDI, _hujjat_izohlari({juft}).get(juft, ""),
            eski=(manba.bolim_id, manba.mol_id, manba.holat),
        )
        yoz(kim, manba, "soni", eski_soni, eski_soni - soni)
        # Σ aynan `soni`ga kamayadi va 1C qoldig'idan pastga tushmaydi (farq <= 0).
        if _jami(*juft) != jami_oldin - soni or farq(manba.av, manba.filial) > 0:
            raise AmalXato("Taqsimot yig'indisi 1C qoldig'idan kamayib ketadi.")


def ayir_va_yoz(qator: Taqsimot, soni: Decimal, kim, sabab: str, hujjat_izoh: str = "") -> None:
    """Qulflangan qatordan `soni` donani olib tashlaydi (0 qolsa o'chiriladi) va `TaqsimotHarakat` + Jurnal yozadi.
    Qulflash, son va invariant tekshiruvi — chaqiruvchining vazifasi (masalan, `chiqimlar.servis.tasdiqla`)."""
    eski_soni = qator.soni
    _ayir(qator, soni)
    _harakat(qator, soni, kim, sabab, hujjat_izoh[:255], eski=(qator.bolim_id, qator.mol_id, qator.holat))
    yoz(kim, qator, "soni", eski_soni, eski_soni - soni)


def _ozgartir(qator, soni, kim, sabab, *, bolim=_SAQLA, mol=_SAQLA, holat=_SAQLA, hujjat_izoh="") -> Taqsimot:
    """Umumiy amal: `soni` donani (bolim, mol, holat) yangi qiymatiga o'tkazadi; o'zgarmaydiganlari `_SAQLA`.
    `bolim`/`mol` — pk yoki None."""
    soni = _tekshir_soni(soni, qator.soni)
    with transaction.atomic():
        manba, qulflangan = _qulfla(qator)
        _tekshir_arxiv(manba)
        # Qulflangan qatordan qayta tekshiriladi: boshqa foydalanuvchi oraliqda o'zgartirgan bo'lishi mumkin.
        soni = _tekshir_soni(soni, manba.soni)
        eski = (manba.bolim_id, manba.mol_id, manba.holat)
        yangi = (
            manba.bolim_id if bolim is _SAQLA else bolim,
            manba.mol_id if mol is _SAQLA else mol,
            manba.holat if holat is _SAQLA else holat,
        )
        if yangi == eski:
            raise AmalXato("Qator allaqachon shu qiymatda; o'zgartirish shart emas.")
        juft = (manba.av_id, manba.filial_id)
        jami_oldin = _jami(*juft)

        # Nishon qator ham qulflangan to'plamdan olinadi (`_qulfla` hamma qatorni pk tartibida qulflagan).
        nishon = next((t for t in qulflangan if (t.bolim_id, t.mol_id, t.holat) == yangi), None)
        eski_manba_soni = manba.soni
        _ayir(manba, soni)
        if nishon is None:
            try:
                with transaction.atomic():  # savepoint: unikal kalit buzilsa tushunarli xato (500 emas)
                    nishon = Taqsimot.objects.create(
                        av_id=juft[0], filial_id=juft[1], bolim_id=yangi[0], mol_id=yangi[1], holat=yangi[2],
                        soni=soni,
                    )
            except IntegrityError:
                # Shu qiymatli qatorni oraliqda boshqa amal (masalan, 1C sinxroni) yaratgan.
                raise AmalXato(
                    "Taqsimot bir vaqtda boshqa amal bilan o'zgardi. Sahifani yangilab, qayta urinib ko'ring."
                ) from None
            eski_nishon_soni = NOL
        else:
            eski_nishon_soni = nishon.soni
            nishon.soni = eski_nishon_soni + soni
            nishon.save(update_fields=["soni"])

        _harakat(manba, soni, kim, sabab, hujjat_izoh, eski=eski, yangi=yangi)
        yoz(kim, manba, "soni", eski_manba_soni, eski_manba_soni - soni)
        yoz(kim, nishon, "soni", eski_nishon_soni, nishon.soni)
        if _jami(*juft) != jami_oldin:
            raise AmalXato("Taqsimot yig'indisi o'zgarib ketdi.")
        return nishon


def _tekshir_soni(soni, chegara: Decimal) -> Decimal:
    """`0 < soni <= chegara`, ko'pi bilan 3 kasr xonasi."""
    try:
        soni = soni if isinstance(soni, Decimal) else Decimal(str(soni))
        togri = soni.is_finite()
    except (InvalidOperation, ValueError):
        togri = False
    if not togri:
        raise AmalXato("Sonni to'g'ri kiriting.")
    if soni <= 0:
        raise AmalXato("Soni noldan katta bo'lishi kerak.")
    if soni.as_tuple().exponent < -3:
        raise AmalXato("Sonda ko'pi bilan 3 ta kasr xonasi bo'lishi mumkin.")
    if soni > chegara:
        raise AmalXato(f"Soni qatordagi miqdordan ({chegara:f}) oshib ketdi.")
    return soni


def _qulfla(qator) -> tuple:
    """Shu (AV, filial) ning barcha qatorlarini pk tartibida qulflaydi (manba va birlashish nishoni ular orasida).
    (manba, barcha qulflangan qatorlar) qaytaradi."""
    qulflangan = list(
        Taqsimot.objects.select_for_update().filter(av_id=qator.av_id, filial_id=qator.filial_id).order_by("pk")
    )
    manba = next((t for t in qulflangan if t.pk == qator.pk), None)
    if manba is None:
        raise AmalXato("Qator topilmadi: boshqa foydalanuvchi uni o'zgartirgan. Sahifani yangilang.")
    return manba, qulflangan


def _tekshir_arxiv(qator) -> None:
    """Arxiv AV (barcha filiallardagi 1C qoldig'i <= 0) bilan amal bajarilmaydi."""
    jami = AVQoldiq.objects.filter(av_id=qator.av_id).aggregate(s=Sum("soni"))["s"] or NOL
    if jami <= 0:
        raise AmalXato("Arxivdagi AV bilan amal bajarib bo'lmaydi.")


def _jami(av_id, filial_id) -> Decimal:
    return Taqsimot.objects.filter(av_id=av_id, filial_id=filial_id).aggregate(s=Sum("soni"))["s"] or NOL


def _ayir(qator, soni) -> None:
    """Qatordan `soni` ayiradi; 0 qolsa qator o'chiriladi."""
    qolgan = qator.soni - soni
    if qolgan > 0:
        qator.soni = qolgan
        qator.save(update_fields=["soni"])
    else:
        Taqsimot.objects.filter(pk=qator.pk).delete()


def _harakat(qator, soni, kim, sabab, hujjat_izoh, *, eski, yangi=None) -> None:
    """TaqsimotHarakat; eski/yangi — (bolim_id, mol_id, holat); yangi=None — miqdor olib tashlandi."""
    yangi_bolim, yangi_mol, yangi_holat = yangi or (None, None, "")
    TaqsimotHarakat.objects.create(
        av_id=qator.av_id, filial_id=qator.filial_id,
        eski_bolim_id=eski[0], eski_mol_id=eski[1], eski_holat=eski[2],
        yangi_bolim_id=yangi_bolim, yangi_mol_id=yangi_mol, yangi_holat=yangi_holat,
        soni=soni, kim=kim, sabab=sabab, hujjat_izoh=hujjat_izoh,
    )
