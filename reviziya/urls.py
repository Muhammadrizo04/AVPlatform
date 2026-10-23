from django.urls import path

from . import views

app_name = "reviziya"

urlpatterns = [
    path("", views.royxat, name="royxat"),
    path("yangi/", views.yangi, name="yangi"),
    path("<int:pk>/", views.sahifa, name="sahifa"),
    path("<int:pk>/yakunla/", views.yakunla_view, name="yakunla"),
    path("<int:pk>/bekor/", views.bekor_view, name="bekor"),
    path("<int:pk>/qolla/", views.qolla_view, name="qolla"),
    path("<int:pk>/yop/", views.yop_view, name="yop"),
    path("<int:pk>/excel/", views.excel, name="excel"),
    path("<int:pk>/pdf/", views.pdf, name="pdf"),
]
