from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from hisoblar.huquqlar import amal_kerak

urlpatterns = [
    path("", amal_kerak("korish")(TemplateView.as_view(template_name="panel/bosh.html")), name="bosh"),
    path("", include("hisoblar.urls")),
    path("admin/", admin.site.urls),
]
