from django.urls import path

from . import sozlamalar, views

app_name = "panel"

urlpatterns = [
    path("", views.bosh, name="bosh"),
    path("sozlamalar/foydalanuvchilar/", sozlamalar.foydalanuvchilar, name="foydalanuvchilar"),
    path("sozlamalar/foydalanuvchilar/<int:pk>/", sozlamalar.foydalanuvchi_tahrir, name="foydalanuvchi_tahrir"),
    path("sozlamalar/av-turlari/", sozlamalar.av_turlari, name="av_turlari"),
    path("sozlamalar/av-turlari/<int:pk>/", sozlamalar.av_turi_tahrir, name="av_turi_tahrir"),
    path("sozlamalar/umumiy/", sozlamalar.umumiy, name="umumiy"),
    path("sozlamalar/yorliq-olchamlari/", sozlamalar.yorliq_olchamlari, name="yorliq_olchamlari"),
    path("sozlamalar/yorliq-olchamlari/<int:pk>/", sozlamalar.yorliq_olchami_tahrir, name="yorliq_olchami_tahrir"),
    path("sozlamalar/ulanish/", sozlamalar.ulanish, name="ulanish"),
    path("sozlamalar/ulanish/sinxronla/", sozlamalar.hozir_sinxronla, name="hozir_sinxronla"),
    path("sozlamalar/sinxron-jurnal/", sozlamalar.sinxron_jurnal, name="sinxron_jurnal"),
    path("sozlamalar/jurnal/", sozlamalar.jurnal, name="jurnal"),
]
