# Generated by Django 4.2.7 on 2023-11-12 18:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gbp_ps", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="buildprocess",
            name="phase",
            field=models.CharField(db_index=True, max_length=255),
        )
    ]
