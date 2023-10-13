from django.db import connection, migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0005_migrate_site_to_location_part_2"),
    ]

    nautobot_run_before = [
        ("dcim", "0040_remove_region_and_site"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="onboardingtask",
            name="site",
        )
    ]

    def __init__(self, name, app_label):
        super().__init__(name, app_label)
        if self.nautobot_run_before:
            recorder = migrations.recorder.MigrationRecorder(connection)
            applied_migrations = recorder.applied_migrations()
            if ("nautobot_device_onboarding", "0001_initial") in applied_migrations:
                for migration in self.nautobot_run_before:
                    if migration not in applied_migrations:
                        self.run_before.append(migration)
