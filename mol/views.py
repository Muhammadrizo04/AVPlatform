import re
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from hisoblar.huquqlar import amal_kerak, filial_bilan_chekla, huquqi_bor
from hisoblar.parametrlar import son
from onec.models import AV, Filial
from vositalar.amortizatsiya import dona_narxi
from vositalar.bayroqlar import BAYROQLAR
from vositalar.models import Holat

from . import sorovlar
from .models import MolAkt
from .pdf import akt_pdf as akt_pdf_yarat
from .servis import AktXato, akt_bekor_qil, akt_tasdiqla as akt_tasdiqla_xizmat, akt_yarat

NOL = Decimal("0")
TIYIN = Decimal("0.01")
AKT_SAHIFA_HAJMI = 50
AKT_RAQAMI = re.compile(r"^(?:ma-?)?0*(\d{1,9})$", re.IGNORECASE)


def _id(qiymat) -> int:
    """So'rovdagi id; noto'g'ri bo'lsa 0 (hech narsaga mos kelmaydi)."""
    return son(qiymat) or 0


@amal_kerak("korish")
def xodimlar(request):
    royxat = list(sorovlar.korinadigan_xodimlar(request.user).order_by("ism", "pk"))
    yigindi = sorovlar.xodim_yigindilari(request.user)
    for x in royxat:
        x.av_soni, x.qiymat = yigindi.get(x.pk, (NOL, NOL))
    return render(
        request, "mol/xodimlar.html",
        {"xodimlar": royxat, "akt_huquqi": huquqi_bor(request.user, "mol_akt")},
    )


@amal_kerak("korish")
def xodim(request, pk):
    x = sorovlar.korinadigan_xodimlar(request.user).filter(pk=pk).first()
    if x is None:
        raise Http404
    qatorlar = list(
        sorovlar.ruxsat_taqsimot(request.user)
        .filter(mol=x)
        .select_related("av", "filial", "bolim__ota__ota")
        .order_by("av__nomi", "filial__nomi", "pk")
    )
    narxlar = {
        av.pk: dona_narxi(av.jami_summa, av.jami_soni)
        for av in AV.objects.qoldiq_bilan().filter(pk__in={t.av_id for t in qatorlar})
    }
    holatlar = dict(Holat.choices)
    for t in qatorlar:
        t.qiymat = t.soni * narxlar.get(t.av_id, NOL)
        t.holat_nomi = holatlar.get(t.holat, t.holat)
    aktlar = sorovlar.korinadigan_aktlar(request.user).filter(Q(topshiruvchi=x) | Q(qabul_qiluvchi=x))
    kontekst = {
        "xodim": x,
        "qatorlar": qatorlar,
        "jami_soni": sum((t.soni for t in qatorlar), NOL),
        "jami_qiymat": sum((t.qiymat for t in qatorlar), NOL),
        "aktlar": aktlar.order_by("-raqam"),
        "akt_huquqi": huquqi_bor(request.user, "mol_akt"),
    }
    return render(request, "mol/xodim.html", kontekst)


@amal_kerak("korish")
def ketganlar(request):
    qatorlar = BAYROQLAR["ketgan_xodimda"].so_rov(request.user, timezone.localdate()).order_by("mol__ism", "mol_id", "pk")
    guruhlar: dict[int, dict] = {}
    for t in qatorlar:
        g = guruhlar.setdefault(t.mol_id, {"xodim": t.mol, "qatorlar": [], "soni": NOL})
        g["qatorlar"].append(t)
        g["soni"] += t.soni
    return render(
        request,
        "mol/ketganlar.html",
        {"guruhlar": list(guruhlar.values()), "akt_huquqi": huquqi_bor(request.user, "mol_akt")},
    )


def _topshiruvchi(request, qiymat):
    """(topshiruvchi yoki None=МОЛ'siz qatorlar, ruxsat etilgan taqsimot qatorlari)."""
    top = None
    qatorlar = sorovlar.ruxsat_taqsimot(request.user).filter(av__in=AV.objects.faol().values("pk"))
    if (qiymat or "").strip():
        top = sorovlar.korinadigan_xodimlar(request.user).filter(pk=_id(qiymat)).first()
        if top is None:
            raise Http404
        qatorlar = qatorlar.filter(mol=top)
    else:
        qatorlar = qatorlar.filter(mol__isnull=True)
    return top, qatorlar.select_related("av", "filial", "bolim__ota__ota").order_by("av__nomi", "filial__nomi", "pk")


def _akt_yaratish(request, top, qatorlar) -> MolAkt:
    qabul = sorovlar.faol_xodimlar(request.user).filter(pk=_id(request.POST.get("qabul"))).first()
    if qabul is None:
        raise AktXato("Qabul qiluvchini tanlang (faol xodim bo'lishi kerak).")
    mavjud = {t.pk: t for t in qatorlar}
    tanlangan = list(dict.fromkeys(request.POST.getlist("tanlangan")))
    tanlov = []
    for qiymat in tanlangan:
        t = mavjud.get(_id(qiymat))
        if t is None:
            raise AktXato("Tanlangan qator topshiruvchining ruxsat etilgan qatorlari orasida yo'q.")
        soni = (request.POST.get(f"soni_{t.pk}") or "").strip() or t.soni
        tanlov.append((t, soni))
    return akt_yarat(top, qabul, tanlov, request.user, izoh=request.POST.get("izoh", "").strip())


# Formada ko'pi bilan shuncha qator ko'rsatiladi (ko'p qator — sahifa og'ir, POST maydonlar chegarasi).
AKT_QATOR_CHEGARASI = 200


def _korinadigan_qatorlar(qatorlar, manba, tanlanganlar: set[int]):
    """Formada ko'rsatiladigan qatorlar: `q` (inv. raqam / nom) va `filial` filtri, chegaralangan;
    tanlangan qatorlar har doim ko'rsatiladi. (qatorlar, kesildimi) qaytaradi."""
    qs = qatorlar
    q = (manba.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(av__inv_raqam__icontains=q) | Q(av__nomi__icontains=q))
    filial_id = son(manba.get("filial"))
    if filial_id:
        qs = qs.filter(filial_id=filial_id)
    royxat = list(qs[: AKT_QATOR_CHEGARASI + 1])
    kesildi = len(royxat) > AKT_QATOR_CHEGARASI
    royxat = royxat[:AKT_QATOR_CHEGARASI]
    yetmagan = tanlanganlar - {t.pk for t in royxat}
    if yetmagan:
        royxat = list(qatorlar.filter(pk__in=yetmagan)) + royxat
    return royxat, kesildi


@amal_kerak("mol_akt")
def akt_yangi(request):
    manba = request.POST if request.method == "POST" else request.GET
    top, qatorlar = _topshiruvchi(request, manba.get("topshiruvchi"))
    xato, status = "", 200
    tanlanganlar: set[int] = set()
    if request.method == "POST":
        try:
            akt = _akt_yaratish(request, top, list(qatorlar))
        except AktXato as e:
            xato, status = str(e), 400
        else:
            messages.success(request, f"Qoralama akt {akt.nomi} yaratildi.")
            return redirect("mol:akt", pk=akt.pk)
        tanlanganlar = {pk for pk in (son(v) for v in request.POST.getlist("tanlangan")) if pk}
    else:
        # `?qator=<pk>` (AV kartochkasidan): shu AV qatorlari ko'rsatiladi, ko'rsatilgan qator oldindan belgilanadi.
        pk = son(request.GET.get("qator"))
        tanlangan = qatorlar.filter(pk=pk).first() if pk else None
        if tanlangan is not None:
            tanlanganlar = {tanlangan.pk}
            qatorlar = qatorlar.filter(av_id=tanlangan.av_id)
    korinadigan, kesildi = _korinadigan_qatorlar(qatorlar, manba, tanlanganlar)
    kontekst = {
        "topshiruvchi": top,
        "qatorlar": korinadigan,
        "tanlanganlar": tanlanganlar,
        "kesildi": kesildi,
        "chegara": AKT_QATOR_CHEGARASI,
        "filiallar": filial_bilan_chekla(Filial.objects.all(), request.user, "pk").order_by("nomi"),
        "qabul_qiluvchilar": [x for x in sorovlar.faol_xodimlar(request.user).order_by("ism", "pk") if not top or x.pk != top.pk],
        "xodimlar": sorovlar.korinadigan_xodimlar(request.user).order_by("ism", "pk"),
        "xato": xato,
        "forma": request.POST if request.method == "POST" else {},
        "params": manba,
    }
    return render(request, "mol/akt_yangi.html", kontekst, status=status)


def _sana(qiymat) -> date | None:
    try:
        return date.fromisoformat((qiymat or "").strip())
    except ValueError:
        return None


@amal_kerak("korish")
def akt_royxat(request):
    """Barcha ko'rinadigan aktlar (qoralama, tasdiqlangan, bekor) — yangisi tepada."""
    qs = sorovlar.korinadigan_aktlar(request.user).select_related("tuzdi").order_by("-raqam")
    holat = request.GET.get("holat", "")
    if holat in MolAkt.Holat.values:
        qs = qs.filter(holat=holat)
    q = request.GET.get("q", "").strip()
    if q:
        shart = Q(topshiruvchi__ism__icontains=q) | Q(qabul_qiluvchi__ism__icontains=q)
        raqam = AKT_RAQAMI.match(q)
        if raqam:
            shart |= Q(raqam=int(raqam.group(1)))
        qs = qs.filter(shart)
    dan, gacha = _sana(request.GET.get("dan")), _sana(request.GET.get("gacha"))
    if dan:
        qs = qs.filter(sana__gte=dan)
    if gacha:
        qs = qs.filter(sana__lte=gacha)
    sahifa = Paginator(qs, AKT_SAHIFA_HAJMI).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "mol/akt_royxat.html", {
        "sahifa": sahifa, "query": params.urlencode(), "holat": holat, "holatlar": MolAkt.Holat.choices,
        "params": request.GET, "akt_huquqi": huquqi_bor(request.user, "mol_akt"),
    })


def _akt_yoki_404(request, pk) -> MolAkt:
    akt = sorovlar.korinadigan_aktlar(request.user).filter(pk=pk).first()
    if akt is None:
        raise Http404
    return akt


@amal_kerak("korish")
def akt(request, pk):
    a = _akt_yoki_404(request, pk)
    qatorlar = list(a.qatorlar.select_related("av", "filial", "bolim__ota__ota").order_by("pk"))
    narxlar = sorovlar.akt_narxlari(a, qatorlar)
    holatlar = dict(Holat.choices)
    for q in qatorlar:
        q.qiymat = q.soni * narxlar[q.pk]
        q.holat_nomi = holatlar.get(q.holat, q.holat)
    kontekst = {
        "akt": a,
        "qatorlar": qatorlar,
        "jami_qiymat": sum((q.qiymat for q in qatorlar), NOL),
        "tasdiqlash_mumkin": a.holat == MolAkt.Holat.QORALAMA and huquqi_bor(request.user, "mol_akt"),
    }
    return render(request, "mol/akt.html", kontekst)


@require_POST
@amal_kerak("mol_akt")
def akt_tasdiqla(request, pk):
    a = _akt_yoki_404(request, pk)
    try:
        akt_tasdiqla_xizmat(a, request.user)
    except AktXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"Akt {a.nomi} tasdiqlandi.")
    return redirect("mol:akt", pk=a.pk)


@require_POST
@amal_kerak("mol_akt")
def akt_bekor(request, pk):
    a = _akt_yoki_404(request, pk)
    try:
        akt_bekor_qil(a, request.user)
    except AktXato as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"Akt {a.nomi} bekor qilindi.")
    return redirect("mol:akt", pk=a.pk)


@amal_kerak("korish")
def akt_pdf(request, pk):
    a = _akt_yoki_404(request, pk)
    javob = HttpResponse(akt_pdf_yarat(a), content_type="application/pdf")
    javob["Content-Disposition"] = f'inline; filename="{a.nomi}.pdf"'
    return javob
