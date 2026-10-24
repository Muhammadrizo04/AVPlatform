from django.urls import path

from . import mobil, views

app_name = "reviziya"

urlpatterns = [
    path("", views.royxat, name="royxat"),
    path("yangi/", views.yangi, name="yangi"),
    path("komissiya/xodimlar/", views.komissiya_xodimlar, name="komissiya_xodimlar"),
    path("komissiya/qator/", views.komissiya_qator, name="komissiya_qator"),
    path("<int:pk>/", views.sahifa, name="sahifa"),
    path("<int:pk>/yakunla/", views.yakunla_view, name="yakunla"),
    path("<int:pk>/bekor/", views.bekor_view, name="bekor"),
    path("<int:pk>/qolla/", views.qolla_view, name="qolla"),
    path("<int:pk>/yop/", views.yop_view, name="yop"),
    path("<int:pk>/revizorlar/", views.revizorlar_view, name="revizorlar"),
    path("<int:pk>/excel/", views.excel, name="excel"),
    path("<int:pk>/pdf/", views.pdf, name="pdf"),
    # revizorning mobil sahifalari (spec §4)
    path("m/", mobil.reviziyalarim, name="mobil"),
    path("m/yangi/", mobil.yangi, name="mobil_yangi"),
    path("m/<int:pk>/", mobil.xonalar, name="mobil_xonalar"),
    path("m/<int:pk>/skan/", mobil.skan, name="mobil_skan"),
    path("m/<int:pk>/xona-tugadi/", mobil.xona_tugadi_view, name="mobil_xona_tugadi"),
    path("m/<int:pk>/hammasi-bor/", mobil.hammasi_bor, name="mobil_hammasi_bor"),
    path("m/<int:pk>/tarix/", mobil.tarix_view, name="mobil_tarix"),
    path("m/<int:pk>/topish/", mobil.topish, name="mobil_topish"),
    path("m/<int:pk>/saqla/", mobil.saqla, name="mobil_saqla"),
    path("m/qayd/<int:qayd_pk>/tuzat/", mobil.tuzat, name="mobil_tuzat"),
]
