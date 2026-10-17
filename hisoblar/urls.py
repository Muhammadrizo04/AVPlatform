from django.urls import path

from . import views

app_name = "hisoblar"

urlpatterns = [
    path("kirish/", views.KirishView.as_view(), name="kirish"),
    path("chiqish/", views.ChiqishView.as_view(), name="chiqish"),
]
