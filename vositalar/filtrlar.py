"""AV ro'yxati filtrlari. Filial cheklovi har doim qo'llanadi (ro'yxat, Excel va HTMX bo'laklari shu funksiyadan)."""
from django.db.models import Exists, Func, OuterRef, Q, QuerySet, TextField
from django.utils import timezone

from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from hisoblar.parametrlar import son
from onec.models import AV, AVQoldiq

from .bayroqlar import BAYROQLAR, ruxsat_qoldiq
from .models import AVKartochka, Taqsimot


class JsonQiymatlari(Func):
    """jsonb obyektining faqat qiymatlari (kalitlarsiz), qator bilan ajratilgan: `qoshimcha` bo'yicha qidirish uchun
    («cpu» deb qidirilsa kalit nomi emas, qiymatlar solishtiriladi)."""

    template = "(SELECT string_agg(value, chr(10)) FROM jsonb_each_text(%(expressions)s))"
    output_field = TextField()


def _platforma_shart(q: str):
    """«Platforma ma'lumotlari» (qo'shimcha maydonlar qiymatlari va izoh) da `q` bor AV'lar."""
    kartochkalar = AVKartochka.objects.filter(av=OuterRef("pk")).annotate(qiymatlar=JsonQiymatlari("qoshimcha"))
    return Exists(kartochkalar.filter(Q(qiymatlar__icontains=q) | Q(izoh__icontains=q)))


def _bayroq_av_idlari(kalit: str, user) -> list[int]:
    natija = BAYROQLAR[kalit].so_rov(user, timezone.localdate())
    if isinstance(natija, list):
        return [av.pk for av in natija]
    if natija.model is not AV:  # Taqsimot, ChiqimHujjat — AV'ga `av_id` orqali
        return list(natija.values_list("av_id", flat=True))
    return list(natija.values_list("pk", flat=True))


def av_filtrla(qs: QuerySet, params, user) -> QuerySet:
    """`qs` (AV) ni foydalanuvchi huquqi va `params` (q, filial, bolim, turi, holat, mol, mol_ism, arxiv, guruh, bayroq) bilan
    chegaralaydi. Arxivsiz: ruxsat etilgan filialda musbat qoldig'i bor faol AV'lar (bayroqlar bilan bir xil qoida);
    `arxiv=1`: arxiv AV'lar, ruxsat etilgan `filial_rekvizit` bo'yicha."""
    arxiv = params.get("arxiv") == "1"
    if arxiv:
        qs = filial_bilan_chekla(qs.arxiv(), user, "filial_rekvizit")
    else:
        # soni/summa — faqat ruxsat etilgan filiallardagi qoldiq (boshqa filialdagi qism ko'rinmaydi)
        qs = qs.qoldiq_bilan(ruxsat_filial_idlar(user)).faol().filter(ruxsat_qoldiq(user))

    q = (params.get("q") or "").strip()
    if q:
        # 1C maydonlari (inv. raqam, nomi) va platforma ma'lumotlari (masalan, «i7-14», «16 GB»)
        qs = qs.filter(Q(inv_raqam__icontains=q) | Q(nomi__icontains=q) | _platforma_shart(q))

    filial = son(params.get("filial"))
    if filial is not None:
        ruxsat = ruxsat_filial_idlar(user)
        if ruxsat is not None and filial not in ruxsat:
            return qs.none()
        if arxiv:
            qs = qs.filter(filial_rekvizit_id=filial)
        else:
            qs = qs.filter(Exists(AVQoldiq.objects.filter(av=OuterRef("pk"), filial_id=filial, soni__gt=0)))

    turi = son(params.get("turi"))
    if turi is not None:
        qs = qs.filter(turi_id=turi)

    taqsimot = {}
    for maydon, nom in (("bolim", "bolim_id"), ("mol", "mol_id")):
        qiymat = son(params.get(maydon))
        if qiymat is not None:
            taqsimot[nom] = qiymat
    if params.get("holat"):
        taqsimot["holat"] = params["holat"]
    mol_ism = (params.get("mol_ism") or "").strip()
    if mol_ism:
        taqsimot["mol__ism__icontains"] = mol_ism
    if taqsimot:
        qatorlar = filial_bilan_chekla(Taqsimot.objects.filter(av=OuterRef("pk"), **taqsimot), user)
        qs = qs.filter(Exists(qatorlar))

    if params.get("guruh") == "1":
        qs = qs.filter(jami_soni__gt=1)

    kalit = params.get("bayroq")
    if kalit in BAYROQLAR:
        qs = qs.filter(pk__in=_bayroq_av_idlari(kalit, user))
    return qs


def korinadigan_av_idlari(user, idlar) -> set[int]:
    """`idlar` ichidan foydalanuvchi ko'ra oladigan AV id'lari (`korinadigan_av` bilan bir xil qoida, ro'yxat uchun)."""
    idlar = list(idlar)
    korinadi: set[int] = set()
    for params in ({}, {"arxiv": "1"}):
        korinadi.update(av_filtrla(AV.objects.filter(pk__in=idlar), params, user).values_list("pk", flat=True))
    return korinadi


def korinadigan_av(user, pk) -> AV | None:
    """Foydalanuvchi ko'ra oladigan AV (faol — ruxsat etilgan filialdagi qoldiq, arxiv — ruxsat etilgan
    `filial_rekvizit` bo'yicha) yoki None. Kartochka, HTMX bo'laklari va rasm URL'lari shu funksiyadan foydalanadi."""
    for params in ({}, {"arxiv": "1"}):
        qs = av_filtrla(AV.objects.all(), params, user).select_related(
            "turi__sozlama", "filial_rekvizit", "tashkilot"
        )
        av = qs.filter(pk=pk).first()
        if av is not None:
            return av
    return None
