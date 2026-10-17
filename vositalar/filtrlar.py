"""AV ro'yxati filtrlari. Filial cheklovi har doim qo'llanadi (ro'yxat, Excel va HTMX bo'laklari shu funksiyadan)."""
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from onec.models import AV, AVQoldiq

from .bayroqlar import BAYROQLAR, ruxsat_qoldiq
from .models import Taqsimot


def _son(qiymat) -> int | None:
    try:
        return int(qiymat)
    except (TypeError, ValueError):
        return None


def _bayroq_av_idlari(kalit: str, user) -> list[int]:
    natija = BAYROQLAR[kalit].so_rov(user, timezone.localdate())
    if isinstance(natija, list):
        return [av.pk for av in natija]
    if natija.model is Taqsimot:
        return list(natija.values_list("av_id", flat=True))
    return list(natija.values_list("pk", flat=True))


def av_filtrla(qs: QuerySet, params, user) -> QuerySet:
    """`qs` (AV) ni foydalanuvchi huquqi va `params` (q, filial, bolim, turi, holat, mol, arxiv, guruh, bayroq) bilan
    chegaralaydi. Arxivsiz: ruxsat etilgan filialda musbat qoldig'i bor faol AV'lar (bayroqlar bilan bir xil qoida);
    `arxiv=1`: arxiv AV'lar, ruxsat etilgan `filial_rekvizit` bo'yicha."""
    arxiv = params.get("arxiv") == "1"
    if arxiv:
        qs = filial_bilan_chekla(qs.arxiv(), user, "filial_rekvizit")
    else:
        qs = qs.faol().filter(ruxsat_qoldiq(user))

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(inv_raqam__icontains=q) | Q(nomi__icontains=q))

    filial = _son(params.get("filial"))
    if filial is not None:
        ruxsat = ruxsat_filial_idlar(user)
        if ruxsat is not None and filial not in ruxsat:
            return qs.none()
        if arxiv:
            qs = qs.filter(filial_rekvizit_id=filial)
        else:
            qs = qs.filter(Exists(AVQoldiq.objects.filter(av=OuterRef("pk"), filial_id=filial, soni__gt=0)))

    turi = _son(params.get("turi"))
    if turi is not None:
        qs = qs.filter(turi_id=turi)

    taqsimot = {}
    for maydon, nom in (("bolim", "bolim_id"), ("mol", "mol_id")):
        qiymat = _son(params.get(maydon))
        if qiymat is not None:
            taqsimot[nom] = qiymat
    if params.get("holat"):
        taqsimot["holat"] = params["holat"]
    if taqsimot:
        qatorlar = filial_bilan_chekla(Taqsimot.objects.filter(av=OuterRef("pk"), **taqsimot), user)
        qs = qs.filter(Exists(qatorlar))

    if params.get("guruh") == "1":
        qs = qs.filter(jami_soni__gt=1)

    kalit = params.get("bayroq")
    if kalit in BAYROQLAR:
        qs = qs.filter(pk__in=_bayroq_av_idlari(kalit, user))
    return qs
