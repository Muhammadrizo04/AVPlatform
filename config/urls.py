from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Brauzerlar /favicon.ico ni o'zi so'raydi (HTML'dagi <link> bo'lmagan sahifalarda ham)
    path("favicon.ico", RedirectView.as_view(url=static("panel/ikonka/favicon.ico"), permanent=True)),
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
