from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0003_onboardingtask_label"),
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
