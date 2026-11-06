from django.urls import path

from . import views

app_name = "yorliqlar"

urlpatterns = [
    path("", views.tanlash, name="tanlash"),
    path("pdf/", views.pdf, name="pdf"),
]
