from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0004_migrate_to_extras_role_part_2"),
    ]

    run_before = [
        ("dcim", "0031_remove_device_role_and_rack_role"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="onboardingtask",
            name="role",
        ),
        migrations.RenameField(
            model_name="onboardingtask",
            old_name="new_role",
            new_name="role",
        ),
    ]
