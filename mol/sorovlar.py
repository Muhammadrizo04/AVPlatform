"""МОЛ nazorati so'rovlari: hammasi foydalanuvchi filiallari bilan cheklangan va doimiy sondagi so'rovlar bilan."""
from decimal import Decimal

from django.db.models import Exists, OuterRef, Q, Sum

from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from onec.models import AV, Xodim
from vositalar.amortizatsiya import dona_narxi
from vositalar.models import Taqsimot

from .models import MolAkt, MolAktQator

NOL = Decimal("0")


def ruxsat_taqsimot(user):
    return filial_bilan_chekla(Taqsimot.objects.all(), user, "filial")


def korinadigan_xodimlar(user):
    """Filiali ruxsat etilgan yoki ruxsat etilgan filialda taqsimot qatori bor xodimlar."""
    ushlab = Exists(ruxsat_taqsimot(user).filter(mol=OuterRef("pk")))
    qs = Xodim.objects.all()
    if ruxsat_filial_idlar(user) is not None:
        qs = qs.filter(Q(filial__in=ruxsat_filial_idlar(user)) | ushlab)
    return qs.select_related("filial")


def faol_xodimlar(user):
    """Qabul qiluvchi bo'la oladigan xodimlar."""
    return korinadigan_xodimlar(user).filter(ishdan_bushagan=False, neaktiv=False, onec_da_yoq=False)


def xodim_yigindilari(user, qatorlar=None) -> dict[int, tuple[Decimal, Decimal]]:
    """{xodim_id: (AV soni, qiymat)} — faqat ruxsat etilgan filiallardagi qatorlardan; 2 ta so'rov."""
    qatorlar = ruxsat_taqsimot(user) if qatorlar is None else qatorlar
    juftlar = qatorlar.filter(mol__isnull=False).order_by().values_list("mol_id", "av_id").annotate(s=Sum("soni"))
    juftlar = list(juftlar)
    narxlar = {
        av.pk: dona_narxi(av.jami_summa, av.jami_soni)
        for av in AV.objects.qoldiq_bilan().filter(pk__in={av for _, av, _ in juftlar})
    }
    natija: dict[int, tuple[Decimal, Decimal]] = {}
    for mol_id, av_id, soni in juftlar:
        eski_soni, eski_qiymat = natija.get(mol_id, (NOL, NOL))
        natija[mol_id] = (eski_soni + soni, eski_qiymat + soni * narxlar.get(av_id, NOL))
    return natija


def korinadigan_aktlar(user):
    """Barcha qatorlarining filiali ruxsat etilgan aktlar."""
    idlar = ruxsat_filial_idlar(user)
    qs = MolAkt.objects.select_related("topshiruvchi", "qabul_qiluvchi")
    if idlar is None:
        return qs
    begona = MolAktQator.objects.filter(akt=OuterRef("pk")).exclude(filial__in=idlar)
    return qs.exclude(Exists(begona))
