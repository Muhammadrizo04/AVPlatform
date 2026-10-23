"""Jadval sarlavhasi: ustun bo'yicha saralash havolasi (`panel.saralash.Saralash` bilan)."""
from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def tartib_maydoni(context):
    """Filtr formasi yuborilganda joriy saralash yo'qolmasin — yashirin `tartib` maydoni."""
    saralash = context.get("saralash")
    if saralash is None or not saralash.tanlangan:
        return ""
    return format_html('<input type="hidden" name="tartib" value="{}{}">', "-" if saralash.teskari else "", saralash.kalit)


@register.simple_tag(takes_context=True)
def sahifa_url(context, raqam):
    """Sahifalash havolasi: joriy filtr va tartib parametrlari saqlanadi."""
    params = context["request"].GET.copy()
    params["page"] = raqam
    return "?" + params.urlencode()


@register.simple_tag(takes_context=True)
def saralash_ustuni(context, kalit, nomi, sinf=""):
    """`<th>` — bosilsa shu ustun bo'yicha o'suvchi, qayta bosilsa kamayuvchi. Boshqa GET parametrlari saqlanadi,
    sahifa raqami tushadi. Kontekstda `saralash` bo'lmasa oddiy sarlavha."""
    saralash = context.get("saralash")
    if saralash is None or kalit not in saralash.ustunlar:
        return format_html('<th class="{}">{}</th>', sinf, nomi)
    joriy = saralash.kalit == kalit
    params = context["request"].GET.copy()
    params.pop("page", None)
    params["tartib"] = f"-{kalit}" if joriy and not saralash.teskari else kalit
    if not joriy:
        belgi, aria = "cil-swap-vertical", "none"
    elif saralash.teskari:
        belgi, aria = "cil-arrow-bottom", "descending"
    else:
        belgi, aria = "cil-arrow-top", "ascending"
    return format_html(
        '<th class="{}" aria-sort="{}"><a class="saralash{}" href="?{}">{}<i class="{}" aria-hidden="true"></i></a></th>',
        sinf, aria, " faol" if joriy else "", params.urlencode(), nomi, belgi,
    )
