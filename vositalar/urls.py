from django.urls import path

from . import views

app_name = "vositalar"

urlpatterns = [
    path("", views.royxat, name="royxat"),
    path("excel/", views.royxat_excel, name="royxat_excel"),
    path("ommaviy/", views.ommaviy, name="ommaviy"),
]
