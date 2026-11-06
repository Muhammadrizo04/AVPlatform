from django.urls import path

from . import views

app_name = "hisobotlar"

urlpatterns = [
    path("tozalash/", views.tozalash, name="tozalash"),
    path("kesim/", views.kesim, name="kesim"),
    path("mol-qaydnoma/", views.mol_qaydnoma, name="mol_qaydnoma"),
    path("bolim-qaydnoma/", views.bolim_qaydnoma, name="bolim_qaydnoma"),
    path("muddat/", views.muddat, name="muddat"),
]
