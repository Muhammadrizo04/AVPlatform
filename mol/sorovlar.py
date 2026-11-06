"""МОЛ nazorati so'rovlari: hammasi foydalanuvchi filiallari bilan cheklangan va doimiy sondagi so'rovlar bilan."""
from decimal import Decimal

from django.db.models import Exists, OuterRef, Q, Sum

from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from onec.models import Xodim
from vositalar.models import Taqsimot
from vositalar.narx import filial_narxlari

from .models import MolAkt, MolAktQator

NOL = Decimal("0")
# `Xodim.ketgan` ning so'rov ko'rinishi
KETGAN = Q(ishdan_bushagan=True) | Q(neaktiv=True) | Q(ochirilgan=True) | Q(onec_da_yoq=True)


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
    return korinadigan_xodimlar(user).exclude(KETGAN)


def xodim_yigindilari(user, qatorlar=None) -> dict[int, tuple[Decimal, Decimal]]:
    """{xodim_id: (AV soni, qiymat)} — faqat ruxsat etilgan filiallardagi qatorlardan; 2 ta so'rov."""
    qatorlar = ruxsat_taqsimot(user) if qatorlar is None else qatorlar
    juftlar = list(
        qatorlar.filter(mol__isnull=False).order_by().values_list("mol_id", "av_id", "filial_id").annotate(s=Sum("soni"))
    )
    narx = filial_narxlari({av_id for _, av_id, _, _ in juftlar})
    natija: dict[int, tuple[Decimal, Decimal]] = {}
    for mol_id, av_id, filial_id, soni in juftlar:
        eski_soni, eski_qiymat = natija.get(mol_id, (NOL, NOL))
        natija[mol_id] = (eski_soni + soni, eski_qiymat + soni * narx(av_id, filial_id))
    return natija


def akt_narxlari(akt, qatorlar) -> dict[int, Decimal]:
    """{akt qatori pk: bir dona narxi}. Tasdiqlangan akt — tasdiqlash paytida saqlangan narx (keyin o'zgarmaydi);
    qoralama — joriy 1C qoldig'idan (summa / soni)."""
    tasdiqlangan = akt.holat == MolAkt.Holat.TASDIQLANGAN
    narx = filial_narxlari({q.av_id for q in qatorlar if not (tasdiqlangan and q.dona_narxi is not None)})
    return {
        q.pk: q.dona_narxi if tasdiqlangan and q.dona_narxi is not None else narx(q.av_id, q.filial_id)
        for q in qatorlar
    }


def korinadigan_aktlar(user):
    """Barcha qatorlarining filiali ruxsat etilgan aktlar."""
    idlar = ruxsat_filial_idlar(user)
    qs = MolAkt.objects.select_related("topshiruvchi", "qabul_qiluvchi")
    if idlar is None:
        return qs
    begona = MolAktQator.objects.filter(akt=OuterRef("pk")).exclude(filial__in=idlar)
    return qs.exclude(Exists(begona))
