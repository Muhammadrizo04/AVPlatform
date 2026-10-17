from django.urls import path

from . import views

app_name = "vositalar"

urlpatterns = [
    path("", views.royxat, name="royxat"),
    path("excel/", views.royxat_excel, name="royxat_excel"),
    path("ommaviy/", views.ommaviy, name="ommaviy"),
    path("<int:pk>/", views.kartochka, name="kartochka"),
    path("<int:pk>/taqsimot/", views.taqsimot_amal, name="taqsimot_amal"),
    path("<int:pk>/rasm/", views.rasm_yukla, name="rasm_yukla"),
    path("<int:pk>/rasm/asosiy/", views.rasm_asosiy, name="rasm_asosiy"),
    path("rasm/<int:rasm_pk>/", views.rasm_fayl, name="rasm_fayl"),
]
