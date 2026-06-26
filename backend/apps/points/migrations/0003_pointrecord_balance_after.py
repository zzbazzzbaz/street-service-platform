from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("points", "0002_manualpointadjustment"),
    ]

    operations = [
        migrations.AddField(
            model_name="pointrecord",
            name="balance_after",
            field=models.IntegerField(blank=True, null=True, verbose_name="变动后余额"),
        ),
    ]
