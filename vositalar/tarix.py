"""AV tarixi: 1C harakatlari, taqsimot o'zgarishlari, МОЛ aktlari, rasmlar va kartochka jurnali bitta ro'yxatda."""
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from hisoblar.huquqlar import filial_bilan_chekla
from jurnal.models import Jurnal
from mol.sorovlar import korinadigan_aktlar
from onec.models import AV, Harakat1C
from panel.templatetags.raqamlar import son

from .models import AVKartochka, Holat, Rasm, TaqsimotHarakat


@dataclass(frozen=True)
class TarixQator:
    sana: datetime
    tur: str  # "1c" | "qayta_baholash" | "taqsimot" | "holat" | "kochirish" | ... | "mol_akt" | "rasm" | "jurnal"
    matn: str
    kim: str
    # Pul matnga qo'shilmaydi: shablon uni faqat `pul_korish` huquqi borlarga ko'rsatadi.
    summa: Decimal | None = None


# Jurnal maydon kalitlari -> odam tilidagi nomlar (topilmasa — kalitning o'zi, `_` bo'sh joy bilan).
MAYDON_NOMLARI = {
    "ishga_tushgan_sana": "Ishga tushgan sana",
    "xizmat_muddati_oy": "Xizmat muddati (oy)",
    "izoh": "Izoh",
    "nomi": "Nomi",
    "inv_raqam": "Inv. raqam",
    "turi": "AV turi",
    "filial_rekvizit": "Filial (1C rekvizit)",
    "tashkilot": "Tashkilot",
    "chiqarilgan_sana": "Chiqarilgan sana",
    "izoh_1c": "1C izohi",
}


def _qiymat(matn: str) -> str:
    """Jurnaldagi ISO sana (YYYY-MM-DD) -> DD.MM.YYYY; bo'sh -> «—»."""
    if not matn:
        return "—"
    try:
        return date.fromisoformat(matn).strftime("%d.%m.%Y")
    except ValueError:
        return matn


def maydon_nomi(kalit: str) -> str:
    if kalit.startswith("qoshimcha."):
        return f"Qo'shimcha maydon «{kalit.split('.', 1)[1]}»"
    return MAYDON_NOMLARI.get(kalit, kalit.replace("_", " ").capitalize())


def _aware(sana) -> datetime:
    """date yoki datetime -> aware datetime (sana bo'lsa — mahalliy yarim tun)."""
    if isinstance(sana, datetime):
        return sana if timezone.is_aware(sana) else timezone.make_aware(sana)
    if isinstance(sana, date):
        return timezone.make_aware(datetime.combine(sana, time.min))
    raise TypeError(sana)


def _kim(user) -> str:
    return (user.get_full_name() or user.get_username()) if user else ""


def _holat(kalit: str) -> str:
    return Holat(kalit).label if kalit in Holat.values else kalit


def _taqsimot_matni(h: TaqsimotHarakat) -> str:
    eski = " / ".join(x for x in (h.eski_bolim.nomi if h.eski_bolim else "", h.eski_mol.ism if h.eski_mol else "", _holat(h.eski_holat)) if x)
    yangi = " / ".join(x for x in (h.yangi_bolim.nomi if h.yangi_bolim else "", h.yangi_mol.ism if h.yangi_mol else "", _holat(h.yangi_holat)) if x)
    qism = f"{h.get_sabab_display()}: {son(h.soni)} dona, {h.filial.nomi}"
    if eski or yangi:
        qism += f" ({eski or '—'} → {yangi or '—'})"
    if h.hujjat_izoh:
        qism += f" [{h.hujjat_izoh}]"
    return qism


def tarix(av: AV, user) -> list[TarixQator]:
    """`av` bo'yicha `user` ko'ra oladigan voqealar, sana bo'yicha kamayuvchi. 1C harakatlari va taqsimot
    harakatlari — faqat ruxsat etilgan filiallardan, МОЛ aktlari — faqat ko'rinadigan aktlar (boshqa filial bo'lim,
    xodim nomlari va summalari chiqmaydi). Jurnaldan faqat AV va uning kartochkasi qatorlari olinadi (taqsimot
    jurnali `TaqsimotHarakat` bilan takrorlanadi); ular va rasmlar filialga bog'liq emas."""
    natija = []
    for h in filial_bilan_chekla(Harakat1C.objects.filter(av=av), user).select_related("filial"):
        joy = f", {h.filial.nomi}" if h.filial else ""
        hujjat = f"{h.hujjat_turi} {h.hujjat_raqami}".strip()
        if h.soni == 0:  # ПереоценкаОС va shunga o'xshash: soni o'zgarmaydi, faqat qiymat
            natija.append(TarixQator(h.sana, "qayta_baholash", f"1C qayta baholash: {hujjat}{joy}", "1C", h.summa))
        else:
            natija.append(TarixQator(
                h.sana, "1c", f"1C {h.get_vid_display().lower()}: {hujjat} — {son(h.soni)} dona{joy}", "1C", h.summa,
            ))
    harakatlar = filial_bilan_chekla(TaqsimotHarakat.objects.filter(av=av), user).select_related(
        "filial", "kim", "eski_bolim", "yangi_bolim", "eski_mol", "yangi_mol"
    )
    for h in harakatlar:
        natija.append(TarixQator(h.sana, "holat" if h.sabab == "holat" else h.sabab, _taqsimot_matni(h), _kim(h.kim)))
    aktlar = korinadigan_aktlar(user).filter(qatorlar__av=av).distinct().select_related("tuzdi")
    for akt in aktlar:
        kimdan = akt.topshiruvchi.ism if akt.topshiruvchi else "МОЛ'siz"
        natija.append(TarixQator(
            _aware(akt.sana), "mol_akt",
            f"МОЛ akti {akt.nomi} ({akt.get_holat_display().lower()}): {kimdan} → {akt.qabul_qiluvchi.ism}",
            _kim(akt.tuzdi),
        ))
    for r in Rasm.objects.filter(av=av).select_related("kim"):
        natija.append(TarixQator(r.qachon, "rasm", "Rasm yuklandi", _kim(r.kim)))
    kartochka_idlar = [str(pk) for pk in AVKartochka.objects.filter(av=av).values_list("pk", flat=True)]
    shart = Q(obyekt_turi="onec.av", obyekt_id=str(av.pk))
    if kartochka_idlar:
        shart |= Q(obyekt_turi="vositalar.avkartochka", obyekt_id__in=kartochka_idlar)
    for j in Jurnal.objects.filter(shart):
        natija.append(TarixQator(
            j.qachon, "jurnal", f"{maydon_nomi(j.maydon)}: «{_qiymat(j.eski)}» → «{_qiymat(j.yangi)}»", j.kim_nomi
        ))
    natija.sort(key=lambda q: q.sana, reverse=True)
    return natija
