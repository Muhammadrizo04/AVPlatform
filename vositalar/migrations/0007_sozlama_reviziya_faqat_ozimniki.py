from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vositalar", "0006_alter_taqsimotharakat_sabab"),
    ]

    operations = [
        migrations.AddField(
            model_name="sozlama",
            name="reviziya_faqat_ozimniki",
            field=models.BooleanField(default=False),
        ),
    ]
