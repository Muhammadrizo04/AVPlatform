"""Django forma maydonlarini CoreUI klasslari bilan chiqarish: `{% load forma %}` va `{{ maydon|cui }}`."""
from django import forms, template

register = template.Library()


def cui_sinfi(widget) -> str:
    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return "form-check-input"
    if isinstance(widget, forms.Select):  # SelectMultiple ham shu yerga kiradi
        return "form-select"
    return "form-control"


@register.filter
def cui(maydon):
    """Maydonni widget turiga mos klass (form-control / form-select / form-check-input) bilan chiqaradi."""
    sinf = cui_sinfi(maydon.field.widget)
    if maydon.errors:
        sinf += " is-invalid"
    mavjud = maydon.field.widget.attrs.get("class", "")
    return maydon.as_widget(attrs={"class": f"{mavjud} {sinf}".strip()})


@register.filter
def belgilash_katagi(maydon) -> bool:
    return isinstance(maydon.field.widget, forms.CheckboxInput)
