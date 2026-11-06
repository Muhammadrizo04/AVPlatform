from django.db import migrations, models


def bosh_profillarga_hamma_filial(apps, schema_editor):
    """Ilgari bo'sh ro'yxat «hamma filial» degani edi: mavjud foydalanuvchilar kirishini yo'qotmasin."""
    Profil = apps.get_model("hisoblar", "Profil")
    Profil.objects.filter(filiallar__isnull=True).update(hamma_filial=True)


class Migration(migrations.Migration):

    dependencies = [
        ("hisoblar", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="hamma_filial",
            field=models.BooleanField(default=False),
        ),
        # Orqaga qaytarishda ma'lumot o'zgarmaydi: eski sxemada «hech qaysi filial» holatini ifodalab bo'lmaydi.
        migrations.RunPython(bosh_profillarga_hamma_filial, migrations.RunPython.noop),
    ]
