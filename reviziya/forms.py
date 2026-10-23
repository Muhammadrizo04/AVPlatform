"""«Yangi reviziya» formasi: filial, ixtiyoriy bo'lim, revizorlar, izoh (komissiya qatorlari — view'da)."""
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from hisoblar.huquqlar import filial_bilan_chekla, ruxsat_filial_idlar
from hisoblar.models import Rol
from onec.models import Filial
from vositalar.models import Bolim

# Revizor bo'la oladigan rollar (`reviziya_otkazish` huquqi bor rollar)
REVIZOR_ROLLARI = (Rol.REVIZOR, Rol.ADMIN, Rol.HISOBCHI)


class _RevizorMaydoni(forms.ModelMultipleChoiceField):
    def label_from_instance(self, user):
        return f"{user.get_full_name() or user.get_username()} ({user.profil.get_rol_display()})"


class _BolimMaydoni(forms.ModelChoiceField):
    def label_from_instance(self, bolim):
        return f"{bolim.filial.nomi} / {bolim.toliq_nomi}"


def _filiali_bor(user, filial) -> bool:
    """Foydalanuvchi profili filialga ruxsat beradimi (bo'sh ro'yxat — hamma filial)."""
    filiallar = set(user.profil.filiallar.values_list("pk", flat=True))
    return not filiallar or filial.pk in filiallar


class YangiReviziyaForma(forms.Form):
    filial = forms.ModelChoiceField(queryset=Filial.objects.none(), empty_label="Filialni tanlang")
    bolim = _BolimMaydoni(queryset=Bolim.objects.none(), required=False, empty_label="Butun filial")
    revizorlar = _RevizorMaydoni(queryset=get_user_model().objects.none(), widget=forms.CheckboxSelectMultiple)
    izoh = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["filial"].queryset = filial_bilan_chekla(Filial.objects.all(), user, "pk").order_by("nomi")
        self.fields["bolim"].queryset = (
            filial_bilan_chekla(Bolim.objects.filter(faol=True), user)
            .select_related("filial", "ota__ota")
            .order_by("filial__nomi", "nomi")
        )
        revizorlar = get_user_model().objects.filter(is_active=True, profil__rol__in=REVIZOR_ROLLARI)
        idlar = ruxsat_filial_idlar(user)
        if idlar is not None:
            # Faqat so'rovchining filiallarida ishlay oladiganlar (profil filiallari bo'sh — hamma filial)
            revizorlar = revizorlar.filter(Q(profil__filiallar__isnull=True) | Q(profil__filiallar__in=idlar))
        self.fields["revizorlar"].queryset = (
            revizorlar.select_related("profil").distinct().order_by("first_name", "last_name", "username")
        )
        self.fields["revizorlar"].error_messages["required"] = "Kamida bitta revizor tanlang."

    def clean(self):
        tozalangan = super().clean()
        filial, bolim = tozalangan.get("filial"), tozalangan.get("bolim")
        if filial is None:
            return tozalangan
        if bolim is not None and bolim.filial_id != filial.pk:
            self.add_error("bolim", "Bo'lim tanlangan filialga tegishli emas.")
        begonalar = [u for u in tozalangan.get("revizorlar") or [] if not _filiali_bor(u, filial)]
        if begonalar:
            ismlar = ", ".join(u.get_full_name() or u.get_username() for u in begonalar)
            self.add_error("revizorlar", f"Bu filialga ruxsati yo'q: {ismlar}.")
        return tozalangan
