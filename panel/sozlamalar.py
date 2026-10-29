"""Administrator sozlamalari (spec §7.10): foydalanuvchilar, AV turlari, umumiy, yorliq o'lchamlari, 1C, jurnallar."""
import json
import re
from datetime import date
from itertools import zip_longest
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from hisoblar.huquqlar import amal_kerak
from hisoblar.models import Profil, Rol
from jurnal.models import Jurnal
from jurnal.yoz import yoz
from onec.client import OneCClient
from onec.models import AVTuri, Filial, SinxronJurnal
from onec.sinxron import SinxronBand, ketma_ket_xatolar, oxirgi_muvaffaqiyatli, sinxronla
from panel.sahifalash import sahifala
from vositalar.models import AVTuriSozlama, Sozlama, YorliqOlchami

User = get_user_model()
SAHIFA_HAJMI = 50
MAX_MAYDON = 50
MAYDON_TIPLARI = ("matn", "son", "sana", "tanlov")
KALIT_RE = re.compile(r"[a-z0-9_]+")
MAX_PK = 2**62


def client_yarat() -> OneCClient:
    """1C mijozi; testlarda almashtiriladi."""
    return OneCClient.settingsdan()


def _ol(model, pk, **filtr):
    if pk > MAX_PK:
        raise Http404
    try:
        return model.objects.get(pk=pk, **filtr)
    except model.DoesNotExist:
        raise Http404 from None


def _farq_yoz(kim, obyekt, eski: dict, yangi: dict) -> None:
    for maydon, qiymat in yangi.items():
        if eski.get(maydon) != qiymat:
            yoz(kim, obyekt, maydon, eski.get(maydon), qiymat)


# --- foydalanuvchilar ---

class FoydalanuvchiForma(forms.Form):
    username = forms.CharField(label="Login", max_length=150, validators=[UnicodeUsernameValidator()])
    ism = forms.CharField(label="Ism", max_length=150, required=False)
    rol = forms.ChoiceField(label="Rol", choices=Rol.choices)
    filiallar = forms.ModelMultipleChoiceField(
        label="Filiallar", queryset=Filial.objects.order_by("nomi"), required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="Hech biri belgilanmasa — barcha filiallarga ruxsat.",
    )
    parol = forms.CharField(label="Parol", required=False, widget=forms.PasswordInput(render_value=False))
    is_active = forms.BooleanField(label="Faol", required=False, initial=True)

    def __init__(self, *args, user=None, kim=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user, self.kim = user, kim
        if user is None:
            self.fields["parol"].required = True
            del self.fields["is_active"]
        else:
            self.fields["parol"].label = "Yangi parol (bo'sh = o'zgarmaydi)"

    def clean_username(self):
        nom = self.cleaned_data["username"]
        qs = User.objects.filter(username__iexact=nom)
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("Bu login band.")
        return nom

    def clean(self):
        data = super().clean()
        parol = data.get("parol")
        if parol:
            try:
                validate_password(parol, self.user or User(username=data.get("username", "")))
            except ValidationError as xato:
                self.add_error("parol", xato)
        if self.user is not None and self.user.pk == getattr(self.kim, "pk", None):
            if "is_active" in data and not data["is_active"]:
                self.add_error("is_active", "O'zingizni faolsizlantira olmaysiz.")
            if data.get("rol") and data["rol"] != Rol.ADMIN:
                self.add_error("rol", "O'zingizning administrator rolingizni olib tashlay olmaysiz.")
        return data

    @transaction.atomic
    def saqla(self):
        d = self.cleaned_data
        yangi = self.user is None
        user = self.user or User()
        profil = None if yangi else Profil.objects.get_or_create(user=user)[0]
        eski = {} if yangi else {
            "username": user.username, "ism": user.first_name, "rol": profil.rol, "is_active": user.is_active,
            "filiallar": sorted(profil.filiallar.values_list("nomi", flat=True)),
        }
        user.username, user.first_name = d["username"], d["ism"]
        if "is_active" in d:
            user.is_active = d["is_active"]
        if d["parol"]:
            user.set_password(d["parol"])
        elif yangi:
            user.set_unusable_password()
        user.save()
        profil = profil or Profil(user=user)
        profil.rol = d["rol"]
        profil.save()
        profil.filiallar.set(d["filiallar"])
        yangi_q = {
            "username": user.username, "ism": user.first_name, "rol": profil.rol, "is_active": user.is_active,
            "filiallar": sorted(f.nomi for f in d["filiallar"]),
        }
        _farq_yoz(self.kim, user, eski, yangi_q)
        if d["parol"] and not yangi:
            yoz(self.kim, user, "parol", "", "o'zgartirildi")  # parol qiymati jurnalga yozilmaydi
        return user


@amal_kerak("sozlama")
def foydalanuvchilar(request):
    forma = FoydalanuvchiForma(request.POST or None, kim=request.user)
    if request.method == "POST" and forma.is_valid():
        forma.saqla()
        messages.success(request, "Foydalanuvchi yaratildi.")
        return redirect("panel:foydalanuvchilar")
    royxat = User.objects.select_related("profil").prefetch_related("profil__filiallar").order_by("username")
    return render(request, "panel/sozlamalar/foydalanuvchilar.html", {"royxat": royxat, "forma": forma})


@amal_kerak("sozlama")
def foydalanuvchi_tahrir(request, pk):
    user = _ol(User, pk)
    profil = Profil.objects.filter(user=user).first()
    boshlangich = {
        "username": user.username, "ism": user.first_name, "is_active": user.is_active,
        "rol": profil.rol if profil else Rol.REVIZOR,
        "filiallar": profil.filiallar.all() if profil else [],
    }
    forma = FoydalanuvchiForma(request.POST or None, initial=boshlangich, user=user, kim=request.user)
    if request.method == "POST" and forma.is_valid():
        forma.saqla()
        messages.success(request, "Foydalanuvchi saqlandi.")
        return redirect("panel:foydalanuvchilar")
    return render(request, "panel/sozlamalar/forma.html", {
        "forma": forma, "sarlavha": f"Foydalanuvchi: {user.username}", "orqaga": "panel:foydalanuvchilar",
    })


# --- umumiy ---

class UmumiyForma(forms.Form):
    kompaniya_nomi = forms.CharField(label="Kompaniya nomi", max_length=255, required=False)
    reviziya_faqat_ozimniki = forms.BooleanField(
        label="Reviziyani faqat uni ochgan kishi va biriktirilgan revizorlar o'zgartira oladi", required=False,
        help_text="Yoqilsa, boshqa hisobchi yoki revizorlar o'zganing reviziyasini faqat ko'radi: skanerlay, "
                  "yakunlay, bekor qila yoki ochiqqa qaytara olmaydi. Administrator har doim o'zgartira oladi.",
    )


@amal_kerak("sozlama")
def umumiy(request):
    sozlama = Sozlama.ol()
    eski = {"kompaniya_nomi": sozlama.kompaniya_nomi, "reviziya_faqat_ozimniki": sozlama.reviziya_faqat_ozimniki}
    forma = UmumiyForma(request.POST or None, initial=eski)
    if request.method == "POST" and forma.is_valid():
        yangi = {"kompaniya_nomi": forma.cleaned_data["kompaniya_nomi"].strip(),
                 "reviziya_faqat_ozimniki": forma.cleaned_data["reviziya_faqat_ozimniki"]}
        with transaction.atomic():
            _farq_yoz(request.user, sozlama, eski, yangi)
            for maydon, qiymat in yangi.items():
                setattr(sozlama, maydon, qiymat)
            sozlama.save()
        messages.success(request, "Saqlandi.")
        return redirect("panel:umumiy")
    return render(request, "panel/sozlamalar/forma.html", {"forma": forma, "sarlavha": "Umumiy sozlamalar"})


# --- yorliq o'lchamlari ---

def _mm(min_, max_):
    return forms.DecimalField(min_value=min_, max_value=max_, max_digits=5, decimal_places=1)


class OlchamForma(forms.Form):
    nomi = forms.CharField(label="Nomi", max_length=50)
    eni_mm = _mm(20, 120)
    boyi_mm = _mm(15, 120)
    faol = forms.BooleanField(label="Faol", required=False, initial=True)
    standart = forms.BooleanField(label="Standart", required=False)

    def __init__(self, *args, olcham=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.olcham = olcham
        self.fields["eni_mm"].label = "Eni, mm (20–120)"
        self.fields["boyi_mm"].label = "Bo'yi, mm (15–120)"

    def clean(self):
        d = super().clean()
        if d.get("standart") and not d.get("faol"):
            self.add_error("standart", "Nofaol o'lcham standart bo'la olmaydi.")
        elif self.olcham is not None and self.olcham.standart and not d.get("faol"):
            self.add_error("faol", "Standart o'lchamni nofaol qilib bo'lmaydi: avval boshqasini standart qiling.")
        return d

    @transaction.atomic
    def saqla(self, kim):
        d = self.cleaned_data
        yangi = self.olcham is None
        olcham = self.olcham or YorliqOlchami()
        maydonlar = ("nomi", "eni_mm", "boyi_mm", "faol", "standart")
        eski = {} if yangi else {m: getattr(olcham, m) for m in maydonlar}
        if d["standart"]:
            YorliqOlchami.objects.filter(standart=True).exclude(pk=olcham.pk).update(standart=False)
        for m in maydonlar:
            setattr(olcham, m, d[m])
        olcham.save()
        _farq_yoz(kim, olcham, eski, {m: d[m] for m in maydonlar})
        return olcham


@amal_kerak("sozlama")
def yorliq_olchamlari(request):
    forma = OlchamForma(request.POST or None)
    if request.method == "POST" and forma.is_valid():
        forma.saqla(request.user)
        messages.success(request, "O'lcham qo'shildi.")
        return redirect("panel:yorliq_olchamlari")
    royxat = YorliqOlchami.objects.order_by("eni_mm", "boyi_mm", "pk")
    return render(request, "panel/sozlamalar/yorliq_olchamlari.html", {"royxat": royxat, "forma": forma})


@amal_kerak("sozlama")
def yorliq_olchami_tahrir(request, pk):
    olcham = _ol(YorliqOlchami, pk)
    boshlangich = {m: getattr(olcham, m) for m in ("nomi", "eni_mm", "boyi_mm", "faol", "standart")}
    forma = OlchamForma(request.POST or None, initial=boshlangich, olcham=olcham)
    if request.method == "POST" and forma.is_valid():
        forma.saqla(request.user)
        messages.success(request, "O'lcham saqlandi.")
        return redirect("panel:yorliq_olchamlari")
    return render(request, "panel/sozlamalar/forma.html", {
        "forma": forma, "sarlavha": f"Yorliq o'lchami: {olcham.nomi}", "orqaga": "panel:yorliq_olchamlari",
    })


# --- AV turlari ---

class MuddatForma(forms.Form):
    xizmat_muddati_oy = forms.IntegerField(label="Xizmat muddati, oy", min_value=1, max_value=1200, required=False)


def _maydonlarni_o_qi(post) -> tuple[list[dict], list[str]]:
    """POST'dagi parallel ro'yxatlardan maydonlar; (maydonlar, xatolar). Bo'sh qatorlar tushiriladi."""
    ustunlar = [post.getlist(n) for n in ("maydon_kalit", "maydon_nomi", "maydon_tip", "maydon_majburiy", "maydon_tanlov")]
    maydonlar, xatolar, kalitlar = [], [], set()
    for n, (kalit, nomi, tip, majburiy, tanlov) in enumerate(zip_longest(*ustunlar, fillvalue=""), 1):
        kalit, nomi, tip, tanlov = kalit.strip(" "), nomi.strip(), tip.strip(), tanlov.strip()
        if not (kalit or nomi or tanlov):
            continue
        if n > MAX_MAYDON:
            xatolar.append(f"Maydonlar soni {MAX_MAYDON} tadan oshmasin.")
            break
        if not KALIT_RE.fullmatch(kalit):
            xatolar.append(f"{n}-qator: kalit faqat kichik lotin harf, raqam va _ dan iborat bo'lsin.")
            continue
        if kalit in kalitlar:
            xatolar.append(f"{n}-qator: «{kalit}» kaliti takrorlangan.")
            continue
        kalitlar.add(kalit)
        if tip not in MAYDON_TIPLARI:
            xatolar.append(f"{n}-qator: tip {', '.join(MAYDON_TIPLARI)} dan biri bo'lsin.")
            continue
        qiymatlar = list(dict.fromkeys(q.strip() for q in tanlov.split(",") if q.strip()))
        if tip == "tanlov" and not qiymatlar:
            xatolar.append(f"{n}-qator: «tanlov» uchun qiymatlar kiriting (vergul bilan).")
            continue
        maydonlar.append({
            "kalit": kalit, "nomi": nomi[:100] or kalit, "tip": tip, "majburiy": majburiy == "ha",
            "tanlov_qiymatlari": qiymatlar if tip == "tanlov" else [],
        })
    return maydonlar, xatolar


@amal_kerak("sozlama")
def av_turlari(request):
    turlar = AVTuri.objects.select_related("sozlama").order_by("nomi")
    return render(request, "panel/sozlamalar/av_turlari.html", {"turlar": turlar})


@amal_kerak("sozlama")
def av_turi_tahrir(request, pk):
    tur = _ol(AVTuri, pk)
    sozlama = AVTuriSozlama.objects.filter(av_turi=tur).first()
    maydonlar = [{**m, "tanlov": ", ".join(m.get("tanlov_qiymatlari", []))} for m in sozlama.maydonlar] if sozlama else []
    xatolar = []
    forma = MuddatForma(request.POST or None, initial={"xizmat_muddati_oy": sozlama.xizmat_muddati_oy if sozlama else None})
    if request.method == "POST":
        yangi_maydonlar, xatolar = _maydonlarni_o_qi(request.POST)
        maydonlar = _qaytarma(request.POST)
        if forma.is_valid() and not xatolar:
            with transaction.atomic():
                sozlama, _ = AVTuriSozlama.objects.get_or_create(av_turi=tur)
                eski = {"xizmat_muddati_oy": sozlama.xizmat_muddati_oy, "maydonlar": _json(sozlama.maydonlar)}
                sozlama.xizmat_muddati_oy = forma.cleaned_data["xizmat_muddati_oy"]
                sozlama.maydonlar = yangi_maydonlar
                sozlama.save()
                _farq_yoz(request.user, sozlama, eski, {
                    "xizmat_muddati_oy": sozlama.xizmat_muddati_oy, "maydonlar": _json(yangi_maydonlar),
                })
            messages.success(request, "AV turi sozlamasi saqlandi.")
            return redirect("panel:av_turlari")
    return render(request, "panel/sozlamalar/av_turi_tahrir.html", {
        "tur": tur, "forma": forma, "maydonlar": maydonlar, "xatolar": xatolar, "tiplar": MAYDON_TIPLARI,
        "bosh_qatorlar": range(3),
    })


def _json(maydonlar) -> str:
    return json.dumps(maydonlar, ensure_ascii=False)


def _qaytarma(post) -> list[dict]:
    """Xato bo'lsa — foydalanuvchi kiritganini formada qaytarish uchun."""
    ustunlar = [post.getlist(n) for n in ("maydon_kalit", "maydon_nomi", "maydon_tip", "maydon_majburiy", "maydon_tanlov")]
    qatorlar = []
    for kalit, nomi, tip, majburiy, tanlov in list(zip_longest(*ustunlar, fillvalue=""))[:MAX_MAYDON]:
        if kalit or nomi or tanlov:
            qatorlar.append({
                "kalit": kalit, "nomi": nomi, "tip": tip, "majburiy": majburiy == "ha", "tanlov": tanlov,
            })
    return qatorlar


# --- 1C ulanish va sinxron ---

def _url_parolsiz(url: str) -> str:
    """URL ichidagi login:parol (agar bor bo'lsa) olib tashlanadi."""
    try:
        qismlar = urlsplit(url)
        if qismlar.username or qismlar.password:
            return qismlar._replace(netloc=qismlar.netloc.rpartition("@")[2]).geturl()
    except ValueError:
        return ""
    return url


@amal_kerak("sozlama")
def ulanish(request):
    return render(request, "panel/sozlamalar/ulanish.html", {
        "onec_url": _url_parolsiz(settings.ONEC_URL),
        "onec_login": settings.ONEC_LOGIN,  # parol hech qachon ko'rsatilmaydi
        "oxirgi": oxirgi_muvaffaqiyatli(),
        "xatolar": ketma_ket_xatolar(),
    })


@amal_kerak("sinxron")
@require_POST
def hozir_sinxronla(request):
    try:
        natija = sinxronla(client_yarat())
    except SinxronBand:
        messages.warning(request, "Sinxron hozir ishlayapti. Birozdan keyin urinib ko'ring.")
    else:
        if natija.natija == SinxronJurnal.Natija.BAND:
            messages.warning(request, "Sinxron hozir ishlayapti. Birozdan keyin urinib ko'ring.")
        elif natija.natija == SinxronJurnal.Natija.XATO:
            messages.error(request, f"Sinxron xato bilan tugadi: {natija.xato_matni}")
        else:
            messages.success(request, "Sinxron muvaffaqiyatli bajarildi.")
    return redirect("panel:ulanish")


def _sahifa(request, qs):
    return sahifala(request, qs, SAHIFA_HAJMI)


@amal_kerak("sozlama")
def sinxron_jurnal(request):
    sahifa = _sahifa(request, SinxronJurnal.objects.order_by("-boshlandi", "-id"))
    return render(request, "panel/sozlamalar/sinxron_jurnal.html", {"sahifa": sahifa, "query": ""})


def _sana(qiymat: str) -> date | None:
    if not (qiymat.isascii() and len(qiymat) == 10):
        return None
    try:
        return date.fromisoformat(qiymat)
    except ValueError:
        return None


@amal_kerak("sozlama")
def jurnal(request):
    p = request.GET
    qs = Jurnal.objects.all()
    kim = p.get("kim", "").replace("\x00", "").strip()[:100]
    obyekt = p.get("obyekt_turi", "").replace("\x00", "").strip()[:100]
    dan, gacha = _sana(p.get("dan", "")), _sana(p.get("gacha", ""))
    if kim:
        qs = qs.filter(kim_nomi__icontains=kim)
    if obyekt:
        qs = qs.filter(obyekt_turi__icontains=obyekt)
    if dan:
        qs = qs.filter(qachon__date__gte=dan)
    if gacha:
        qs = qs.filter(qachon__date__lte=gacha)
    params = p.copy()
    params.pop("page", None)
    return render(request, "panel/sozlamalar/jurnal.html", {
        "sahifa": _sahifa(request, qs), "query": params.urlencode(),
        "kim": kim, "obyekt_turi": obyekt, "dan": dan or "", "gacha": gacha or "",
    })
