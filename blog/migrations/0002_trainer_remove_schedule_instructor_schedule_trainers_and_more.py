# Generated by Django 5.1 on 2024-08-11 03:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Trainer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("title", models.CharField(blank=True, max_length=100, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "image",
                    models.ImageField(
                        blank=True, null=True, upload_to="trainer_images/"
                    ),
                ),
                ("instagram_url", models.URLField(blank=True, null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name="schedule",
            name="instructor",
        ),
        migrations.AddField(
            model_name="schedule",
            name="Trainers",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="blog.trainer",
            ),
        ),
        migrations.DeleteModel(
            name="Instructor",
        ),
    ]
