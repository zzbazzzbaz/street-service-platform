from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("merchants", "0008_merchant_delete_reason_merchant_deleted_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="merchant",
            name="sort_order",
            field=models.PositiveIntegerField(blank=True, db_index=True, default=None, null=True, verbose_name="排序值"),
        ),
    ]
