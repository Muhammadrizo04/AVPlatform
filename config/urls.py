from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("panel.urls")),
    path("", include("hisoblar.urls")),
    path("av/", include("vositalar.urls")),
    path("yorliqlar/", include("yorliqlar.urls")),
    path("mol/", include("mol.urls")),
    path("chiqimlar/", include("chiqimlar.urls")),
    path("hisobotlar/", include("hisobotlar.urls")),
    path("reviziya/", include("reviziya.urls")),
    path("admin/", admin.site.urls),
]
