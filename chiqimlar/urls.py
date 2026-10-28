from django.urls import path

from . import views

app_name = "chiqimlar"

urlpatterns = [
    path("", views.royxat, name="royxat"),
    path("<int:pk>/", views.tasdiqlash, name="tasdiqlash"),
    path("<int:pk>/qaytar/", views.qaytar, name="qaytar"),
]
