from django.db import migrations, models

import nautobot.dcim.models
import nautobot.extras.models 
import nautobot_device_onboarding


class Migration(migrations.Migration):


    dependencies = [
        ("nautobot_device_onboarding", "0003_onboardingtask_label"),
        ("extras", "0061_role_and_alter_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingtask",
            name="new_role",
            field=nautobot_device_onboarding.models.DeviceLimitedRoleField(blank=True, null=True, on_delete=models.SET_NULL, related_name='onboarding_tasks', to='extras.role'),
        ),
    ]

