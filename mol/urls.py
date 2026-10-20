from django.urls import path

from . import views

app_name = "mol"

urlpatterns = [
    path("", views.xodimlar, name="xodimlar"),
    path("xodim/<int:pk>/", views.xodim, name="xodim"),
    path("ketganlar/", views.ketganlar, name="ketganlar"),
    path("akt/", views.akt_royxat, name="akt_royxat"),
    path("akt/yangi/", views.akt_yangi, name="akt_yangi"),
    path("akt/<int:pk>/", views.akt, name="akt"),
    path("akt/<int:pk>/tasdiqla/", views.akt_tasdiqla, name="akt_tasdiqla"),
    path("akt/<int:pk>/bekor/", views.akt_bekor, name="akt_bekor"),
    path("akt/<int:pk>/pdf/", views.akt_pdf, name="akt_pdf"),
]
