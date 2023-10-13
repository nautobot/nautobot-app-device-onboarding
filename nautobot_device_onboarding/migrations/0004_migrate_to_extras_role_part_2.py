from django.db import migrations


def migrate_to_extras_role(apps, schema_editor):
    OnboardingTask = apps.get_model("nautobot_device_onboarding", "OnboardingTask")
    role_model = apps.get_model("extras", "Role")

    for task_object in OnboardingTask.objects.all():
        # get the new Role object from the existing Role and set it
        if task_object.role:
            task_object.new_role = role_model.objects.get(name=task_object.role.name)
            task_object.save()


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0004_migrate_to_extras_role_part_1"),
    ]

    operations = [
        migrations.RunPython(migrate_to_extras_role, migrations.RunPython.noop),
    ]
