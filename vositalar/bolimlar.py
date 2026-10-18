"""Bo'limlar daraxti: saqlash (yaratish/nomlash/ko'chirish) va faolsizlantirish (spec §7.5).

Daraxt bitta filial ichida; chuqurligi cheklanmagan. Har o'zgarish Jurnalga yoziladi.
"""
from django.db import transaction

from jurnal.yoz import yoz

from .amallar import AmalXato
from .models import Bolim, Taqsimot


def _bolalar_xaritasi(filial_id: int) -> dict:
    """Filial bo'limlari bitta so'rovda: {ota_id: [bo'limlar]}."""
    xarita: dict = {}
    for b in Bolim.objects.filter(filial_id=filial_id).order_by("nomi", "pk"):
        xarita.setdefault(b.ota_id, []).append(b)
    return xarita


def pastkilar(bolim: Bolim) -> list[Bolim]:
    """Bo'limning barcha avlodlari (o'zi kirmaydi)."""
    xarita = _bolalar_xaritasi(bolim.filial_id)
    natija, navbat = [], [bolim.pk]
    while navbat:
        for b in xarita.get(navbat.pop(), []):
            natija.append(b)
            navbat.append(b.pk)
    return natija


def daraxt(filial_id: int) -> list[tuple[Bolim, int, str]]:
    """Filial bo'limlari tartiblangan ro'yxat: [(bo'lim, chuqurlik, to'liq nomi)], ota bolasidan oldin.
    Bitta so'rov; to'liq nom xotiradagi xaritadan hisoblanadi (har satrda qo'shimcha so'rov yo'q)."""
    xarita = _bolalar_xaritasi(filial_id)
    natija: list[tuple[Bolim, int, str]] = []
    stek = [(b, 0, b.nomi) for b in reversed(xarita.get(None, []))]
    while stek:
        b, chuqurlik, toliq = stek.pop()
        natija.append((b, chuqurlik, toliq))
        stek.extend((c, chuqurlik + 1, f"{toliq} / {c.nomi}") for c in reversed(xarita.get(b.pk, [])))
    return natija


SAQLA = object()  # «ota o'zgarmaydi» belgisi (None — aniq ildiz tanlovi)


def bolim_saqla(bolim: Bolim | None, filial, nomi: str, ota=SAQLA, kim=None) -> Bolim:
    """Yangi bo'lim yaratadi (`bolim=None`) yoki mavjudini qayta nomlaydi/ko'chiradi. Xato — `AmalXato`.
    Tahrirda `ota=SAQLA` — ota o'zgarmaydi; `ota=None` — ildizga ko'chiriladi."""
    nomi = (nomi or "").strip()
    if not nomi:
        raise AmalXato("Bo'lim nomini kiriting.")
    if len(nomi) > 255:
        raise AmalXato("Bo'lim nomi 255 belgidan oshmasin.")
    with transaction.atomic():
        if bolim is not None:
            bolim = Bolim.objects.select_for_update().get(pk=bolim.pk)
        o_zgarmaydi = ota is SAQLA
        if o_zgarmaydi:
            ota = None if bolim is None else bolim.ota
        if ota is not None:
            if ota.filial_id != filial.pk:
                raise AmalXato("Ota bo'lim boshqa filialga tegishli.")
            joriy = bolim is not None and ota.pk == bolim.ota_id  # o'zgarmagan ota faolsiz bo'lsa ham mumkin
            if not ota.faol and not joriy:
                raise AmalXato("Ota bo'lim faol emas.")
        if bolim is None:
            yangi = Bolim.objects.create(filial=filial, ota=ota, nomi=nomi)
            yoz(kim, yangi, "yaratildi", "", yangi.toliq_nomi)
            return yangi
        if ota is not None and (ota.pk == bolim.pk or ota.pk in {b.pk for b in pastkilar(bolim)}):
            raise AmalXato("Bo'limni o'zining ichiga yoki pastki bo'limiga ko'chirib bo'lmaydi.")
        eski_nomi, eski_ota = bolim.nomi, bolim.ota
        bolim.nomi, bolim.ota = nomi, ota
        bolim.save(update_fields=["nomi", "ota"])
        if eski_nomi != nomi:
            yoz(kim, bolim, "nomi", eski_nomi, nomi)
        if (eski_ota.pk if eski_ota else None) != (ota.pk if ota else None):
            yoz(kim, bolim, "ota", eski_ota.toliq_nomi if eski_ota else "", ota.toliq_nomi if ota else "")
        return bolim


def bolim_nofaol_qil(bolim: Bolim, kim) -> None:
    """Bo'lim va barcha pastki bo'limlarini faolsizlantiradi. Ichida yoki pastkilarida taqsimot bo'lsa — `AmalXato`."""
    with transaction.atomic():
        bolim = Bolim.objects.select_for_update().get(pk=bolim.pk)
        guruh = [bolim, *pastkilar(bolim)]
        if Taqsimot.objects.filter(bolim_id__in=[b.pk for b in guruh]).exists():
            raise AmalXato("Bo'lim yoki uning pastki bo'limlarida AV bor; avval ularni boshqa bo'limga ko'chiring.")
        for b in guruh:
            if b.faol:
                b.faol = False
                b.save(update_fields=["faol"])
                yoz(kim, b, "faol", True, False)


def bolim_faollashtir(bolim: Bolim, kim) -> None:
    """Faolsiz bo'limni qayta faollashtiradi (ota bo'lim faol bo'lishi shart)."""
    with transaction.atomic():
        bolim = Bolim.objects.select_for_update().get(pk=bolim.pk)
        if bolim.ota is not None and not bolim.ota.faol:
            raise AmalXato("Avval ota bo'limni faollashtiring.")
        if not bolim.faol:
            bolim.faol = True
            bolim.save(update_fields=["faol"])
            yoz(kim, bolim, "faol", False, True)
