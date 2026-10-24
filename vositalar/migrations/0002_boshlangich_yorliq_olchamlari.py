from decimal import Decimal

from django.db import migrations

BOSHLANGICH = [
    {"nomi": "40×30", "eni_mm": Decimal("40"), "boyi_mm": Decimal("30"), "standart": True},
    {"nomi": "58×40", "eni_mm": Decimal("58"), "boyi_mm": Decimal("40"), "standart": False},
]


def olchamlar_yarat(apps, schema_editor):
    YorliqOlchami = apps.get_model("vositalar", "YorliqOlchami")
    for qiymat in BOSHLANGICH:
        YorliqOlchami.objects.get_or_create(nomi=qiymat["nomi"], defaults=qiymat)


def olchamlar_ochir(apps, schema_editor):
    YorliqOlchami = apps.get_model("vositalar", "YorliqOlchami")
    YorliqOlchami.objects.filter(nomi__in=[q["nomi"] for q in BOSHLANGICH]).delete()


class Migration(migrations.Migration):
    dependencies = [("vositalar", "0001_initial")]

    operations = [migrations.RunPython(olchamlar_yarat, olchamlar_ochir)]
