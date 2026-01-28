from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GeekezIntegrationConfig",
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
                ("key", models.CharField(default="default", max_length=50, unique=True)),
                ("control_host", models.CharField(default="127.0.0.1", max_length=255)),
                ("control_port", models.PositiveIntegerField(default=19527)),
                ("control_token_encrypted", models.TextField(blank=True, default="")),
                ("api_server_host", models.CharField(default="127.0.0.1", max_length=255)),
                ("api_server_port", models.PositiveIntegerField(default=12138)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "geekez_integration_configs",
                "verbose_name": "GeekezBrowser 配置",
                "verbose_name_plural": "GeekezBrowser 配置",
            },
        )
    ]
