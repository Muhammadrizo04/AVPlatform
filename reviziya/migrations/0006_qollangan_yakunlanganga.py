from django.db import migrations


def qollanganni_yakunlanganga(apps, schema_editor):
    """«Yopilgan» (qollangan) holati olib tashlandi: bunday reviziyalar «Yakunlangan» bo'ladi."""
    apps.get_model("reviziya", "Reviziya").objects.filter(holat="qollangan").update(holat="yakunlangan")


class Migration(migrations.Migration):
    dependencies = [("reviziya", "0005_qollash_bekor")]

    operations = [migrations.RunPython(qollanganni_yakunlanganga, migrations.RunPython.noop)]
