from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("panel.urls")),
    path("", include("hisoblar.urls")),
    path("av/", include("vositalar.urls")),
    path("mol/", include("mol.urls")),
    path("admin/", admin.site.urls),
]
