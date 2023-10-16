from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0003_onboardingtask_label"),
        # This migration does not actually depend on the below migration but it is added here to
        # prevent Django from failing to migrate due to multiple leaf nodes in the migration graph
        ("nautobot_device_onboarding", "0007_alter_onboardingtask_ip_address"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="onboardingtask",
            options={
                "ordering": ("label",),
            },
        ),
        migrations.AlterUniqueTogether(
            name="onboardingtask",
            unique_together={("label", "ip_address")},
        ),
    ]
