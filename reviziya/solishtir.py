"""Reviziya solishtirish vedomosti (spec §5.1): kutilgan surat va revizor qaydlarini taqqoslaydi.

Faqat o'qiydi — bazaga hech narsa yozmaydi; reviziyaning istalgan holatida ishlaydi (ochiq — jonli ko'rinish).
`solishtir()` ma'lumotni yuklaydi, hisob esa sof `hisobla()` funksiyasida (oddiy ro'yxatlar bilan).

Algoritm har AV bo'yicha:
1. (bo'lim, holat) -> kutilgan va topilgan yig'indilari (МОЛ hisobga olinmaydi).
2. Har bo'limda holatlar bo'yicha teng qismi — `topildi`; holatlar farqi shu bo'limda juftlanadi — `holat_boshqa`
   (kutilgan holatdan topilgan holatga, `min` miqdor). Soni teng bo'lmasa ham juftlanadigan qismi shu yerda
   juftlanadi, shuning uchun keyin har bo'limda faqat bir tomonlama qoldiq (kamomad yoki ortiqcha) qoladi.
3. Kamomad bo'limlari pk tartibida ortiqcha bo'limlari bilan `min(kam, ortiqcha)` juftlashadi — `boshqa_joyda`
   (`bolim_id` — manba, `nishon_bolim_id` — topilgan joy, `holat` — manba holati, `nishon_holat` — topilgan
   holat, agar manbadan farq qilsa, aks holda "").
4. Qolgan kamomad — `topilmadi` (shu bo'limda AV umuman topilmagan) yoki `kam`; qolgan ortiqcha — `ortiqcha`.
   AV'siz (noma'lum QR) qaydlar — `ortiqcha` (`qr_matn` bilan).
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from onec.models import AV
from vositalar.models import Bolim

NOL = Decimal("0")
BOLIMSIZ = "Bo'limsiz"
GURUHLAR = ("topilmadi", "kam", "boshqa_joyda", "holat_boshqa", "ortiqcha", "topildi")
_TARTIB = {guruh: i for i, guruh in enumerate(GURUHLAR)}


@dataclass(frozen=True)
class VedomostQator:
    guruh: str
    av_id: int | None
    av_nomi: str
    inv: str
    bolim_id: int | None
    bolim_nomi: str
    holat: str
    kutilgan: Decimal
    topilgan: Decimal
    farq: Decimal
    nishon_bolim_id: int | None = None
    nishon_holat: str = ""
    qr_matn: str = ""
    kalit: str = field(init=False)

    def __post_init__(self):
        if self.av_id is None:
            kalit = f"ortiqcha:qr:{self.qr_matn}:{self.bolim_id}"
        else:
            kalit = (
                f"{self.guruh}:{self.av_id}:{self.bolim_id}:{self.holat}:{self.nishon_bolim_id}:{self.nishon_holat}"
            )
        object.__setattr__(self, "kalit", kalit)


def _bolim_tartibi(bolim_id):
    """Bo'limlar pk tartibida; bo'limsiz — oxirida."""
    return (bolim_id is None, bolim_id or 0)


def _juftla(chap, ong):
    """Ikki [(kalit, miqdor)] ro'yxatini tartib bo'yicha ochko'z juftlaydi -> [(chap_kalit, ong_kalit, miqdor)]."""
    chap = [list(x) for x in chap]
    ong = [list(x) for x in ong]
    juftlar, i, j = [], 0, 0
    while i < len(chap) and j < len(ong):
        m = min(chap[i][1], ong[j][1])
        juftlar.append((chap[i][0], ong[j][0], m))
        chap[i][1] -= m
        ong[j][1] -= m
        if chap[i][1] == 0:
            i += 1
        if ong[j][1] == 0:
            j += 1
    return juftlar


def _av_hisobi(kutilgan, topilgan):
    """Bitta AV: {(bolim_id, holat): soni} lug'atlari -> [(guruh, bolim, holat, soni, nishon_bolim, nishon_holat)]."""
    natija = []
    bolimlar = sorted({b for b, _ in kutilgan} | {b for b, _ in topilgan}, key=_bolim_tartibi)
    kamomad, ortiqcha = [], []  # [((bolim_id, holat), qoldiq)]
    topilgan_bolimda = defaultdict(lambda: NOL)
    for (b, _), soni in topilgan.items():
        topilgan_bolimda[b] += soni

    for b in bolimlar:
        holatlar = sorted({h for bb, h in kutilgan if bb == b} | {h for bb, h in topilgan if bb == b})
        k_qoldiq, t_qoldiq = [], []
        for h in holatlar:
            k, t = kutilgan.get((b, h), NOL), topilgan.get((b, h), NOL)
            teng = min(k, t)
            if teng > 0:
                natija.append(("topildi", b, h, teng, None, ""))
            if k > teng:
                k_qoldiq.append((h, k - teng))
            if t > teng:
                t_qoldiq.append((h, t - teng))
        for h, nh, m in _juftla(k_qoldiq, t_qoldiq):
            natija.append(("holat_boshqa", b, h, m, None, nh))
        k_jami = sum((s for _, s in k_qoldiq), NOL)
        t_jami = sum((s for _, s in t_qoldiq), NOL)
        # juftlangandan keyin faqat bir tomon qoladi: holatlar tartibida oxiridan kesiladi
        if k_jami > t_jami:
            kamomad.extend(((b, h), s) for h, s in _kesib_qol(k_qoldiq, k_jami - t_jami))
        elif t_jami > k_jami:
            ortiqcha.extend(((b, h), s) for h, s in _kesib_qol(t_qoldiq, t_jami - k_jami))

    jami_kochgan = defaultdict(lambda: NOL)
    kamomad_qoldi = dict(kamomad)
    ortiqcha_qoldi = dict(ortiqcha)
    for (b, h), (nb, nh), m in _juftla(kamomad, ortiqcha):
        jami_kochgan[(b, h, nb, "" if nh == h else nh)] += m
        kamomad_qoldi[(b, h)] -= m
        ortiqcha_qoldi[(nb, nh)] -= m
    for (b, h, nb, nh), m in jami_kochgan.items():
        natija.append(("boshqa_joyda", b, h, m, nb, nh))
    for (b, h), s in kamomad_qoldi.items():
        if s > 0:
            natija.append(("topilmadi" if topilgan_bolimda[b] == 0 else "kam", b, h, s, None, ""))
    for (b, h), s in ortiqcha_qoldi.items():
        if s > 0:
            natija.append(("ortiqcha", b, h, s, None, ""))
    return natija


def _kesib_qol(qoldiqlar, miqdor):
    """Holat_boshqa juftlashidan keyin qolgan `miqdor`ni [(holat, soni)] ro'yxatining oxiridan oladi."""
    natija = []
    for h, s in reversed(qoldiqlar):
        if miqdor <= 0:
            break
        m = min(s, miqdor)
        natija.append((h, m))
        miqdor -= m
    return list(reversed(natija))


def hisobla(kutilganlar, qaydlar, av_malumot, bolim_nomlari) -> list[VedomostQator]:
    """Sof hisob.

    kutilganlar: [(av_id, bolim_id, holat, soni)]; qaydlar: [(av_id | None, bolim_id, holat, soni, qr_matn)];
    av_malumot: {av_id: (nomi, inv)}; bolim_nomlari: {bolim_id: nomi}.
    """
    kutilgan = defaultdict(lambda: defaultdict(lambda: NOL))
    topilgan = defaultdict(lambda: defaultdict(lambda: NOL))
    qr = defaultdict(lambda: [NOL, set()])
    for av_id, b, h, soni in kutilganlar:
        kutilgan[av_id][(b, h)] += soni
    for av_id, b, h, soni, qr_matn in qaydlar:
        if av_id is None:
            qr[(qr_matn, b)][0] += soni
            qr[(qr_matn, b)][1].add(h)
        else:
            topilgan[av_id][(b, h)] += soni

    def bolim_nomi(b):
        return BOLIMSIZ if b is None else bolim_nomlari.get(b, "")

    qatorlar = []
    for av_id in sorted(set(kutilgan) | set(topilgan)):
        nomi, inv = av_malumot.get(av_id, ("", ""))
        for guruh, b, h, m, nb, nh in _av_hisobi(kutilgan.get(av_id, {}), topilgan.get(av_id, {})):
            if guruh == "topildi":
                k, t, farq = m, m, NOL
            elif guruh in ("kam", "topilmadi"):
                k, t, farq = m, NOL, -m
            elif guruh == "ortiqcha":
                k, t, farq = NOL, m, m
            else:  # boshqa_joyda, holat_boshqa — ko'chgan/o'zgargan miqdor
                k, t, farq = m, m, m
            qatorlar.append(
                VedomostQator(
                    guruh=guruh, av_id=av_id, av_nomi=nomi, inv=inv, bolim_id=b, bolim_nomi=bolim_nomi(b),
                    holat=h, kutilgan=k, topilgan=t, farq=farq, nishon_bolim_id=nb, nishon_holat=nh,
                )
            )
    for (qr_matn, b), (soni, holatlar) in qr.items():
        qatorlar.append(
            VedomostQator(
                guruh="ortiqcha", av_id=None, av_nomi="", inv="", bolim_id=b, bolim_nomi=bolim_nomi(b),
                holat=next(iter(holatlar)) if len(holatlar) == 1 else "", kutilgan=NOL, topilgan=soni, farq=soni,
                qr_matn=qr_matn,
            )
        )
    qatorlar.sort(key=lambda q: (_TARTIB[q.guruh], q.av_nomi, q.bolim_nomi, q.kalit))
    return qatorlar


def _bolim_nomlari(filial_id) -> dict[int, str]:
    """Filial bo'limlarining to'liq nomlari («Bino / Xona») — bitta so'rov bilan."""
    satrlar = Bolim.objects.filter(filial_id=filial_id).values_list("pk", "nomi", "ota_id")
    bolimlar = {pk: (nomi, ota_id) for pk, nomi, ota_id in satrlar}
    natija = {}
    for pk in bolimlar:
        qismlar, joriy, korilgan = [], pk, set()
        while joriy in bolimlar and joriy not in korilgan:
            korilgan.add(joriy)
            nomi, ota_id = bolimlar[joriy]
            qismlar.append(nomi)
            joriy = ota_id
        natija[pk] = " / ".join(reversed(qismlar))
    return natija


def solishtir(reviziya) -> list[VedomostQator]:
    kutilganlar = list(reviziya.kutilganlar.values_list("av_id", "bolim_id", "holat", "soni"))
    qaydlar = list(reviziya.qaydlar.values_list("av_id", "bolim_id", "holat", "soni", "qr_matn"))
    av_idlar = {k[0] for k in kutilganlar} | {q[0] for q in qaydlar if q[0] is not None}
    avlar = AV.objects.filter(pk__in=av_idlar).values_list("pk", "nomi", "inv_raqam")
    av_malumot = {pk: (nomi, inv or "") for pk, nomi, inv in avlar}
    return hisobla(kutilganlar, qaydlar, av_malumot, _bolim_nomlari(reviziya.filial_id))


def jamlar(qatorlar) -> dict[str, Decimal]:
    """Guruh -> jami soni: `topildi` uchun topilgan, qolganlari uchun |farq|; barcha olti kalit qaytadi."""
    natija = {guruh: NOL for guruh in GURUHLAR}
    for q in qatorlar:
        natija[q.guruh] += q.topilgan if q.guruh == "topildi" else abs(q.farq)
    return natija
