from django.db import migrations, models

import nautobot.dcim.models
import nautobot.extras.models 


def migrate_to_location_and_role(apps, schema_editor):
    OnboardingTask = apps.get_model("nautobot_device_onboarding", "OnboardingTask")

    for task_object in OnboardingTask.objects.all():
        # get the new Location object from the site and set it
        task_object.location = nautobot.dcim.models.Location.objects.get(name="task_object.site")

        # get the new Role object from the existing Role and set it
        task_object.role = nautobot.extras.models.Role.objects.get(name="task_object.role")

        task_object.save()


class Migration(migrations.Migration):

    dependencies = [
        ("nautobot_device_onboarding", "0004_migrate_site_to_location_part_1"),
    ]

    operations = [
        migrations.RunPython(migrate_to_location_and_role, migrations.RunPython.noop),
    ]
