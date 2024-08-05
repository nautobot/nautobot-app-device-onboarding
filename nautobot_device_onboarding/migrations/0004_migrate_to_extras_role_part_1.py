from django.db import migrations, models
from nautobot.extras.models import RoleField


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0001_initial"),
        ("dcim", "0029_device_and_rack_roles_data_migrations"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingtask",
            name="new_role",
            field=RoleField(
                blank=True, null=True, on_delete=models.SET_NULL, related_name="onboarding_tasks", to="extras.role"
            ),
        ),
    ]
