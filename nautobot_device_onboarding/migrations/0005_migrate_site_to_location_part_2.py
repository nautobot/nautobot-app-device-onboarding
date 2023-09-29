from django.db import migrations


def migrate_to_location(apps, schema_editor):
    OnboardingTask = apps.get_model("nautobot_device_onboarding", "OnboardingTask")
    location_model = apps.get_model("dcim", "Location")

    for task_object in OnboardingTask.objects.all():
        # get the new Location object from the site and set it
        task_object.location = location_model.objects.get(name=task_object.site.name)
        task_object.save()


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0005_migrate_site_to_location_part_1"),
        ("extras", "0062_collect_roles_from_related_apps_roles"),
    ]

    operations = [
        migrations.RunPython(migrate_to_location, migrations.RunPython.noop),
    ]
