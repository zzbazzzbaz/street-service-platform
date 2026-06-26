from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0003_alter_learningcontent_cover"),
    ]

    operations = [
        migrations.AddField(
            model_name="learningcontent",
            name="content_type",
            field=models.CharField(
                choices=[
                    ("article", "图文文章"),
                    ("image", "图片内容"),
                    ("video", "视频内容"),
                ],
                default="article",
                max_length=20,
                verbose_name="内容类型",
            ),
        ),
    ]
