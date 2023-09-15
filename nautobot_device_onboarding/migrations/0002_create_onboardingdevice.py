from django.db import migrations


def create_missing_onboardingdevice(apps, schema_editor):
    Device = apps.get_model("dcim", "Device")
    OnboardingDevice = apps.get_model("nautobot_device_onboarding", "OnboardingDevice")

    for device in Device.objects.filter(onboardingdevice__isnull=True):
        OnboardingDevice.objects.create(device=device)


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_missing_onboardingdevice, migrations.RunPython.noop),
    ]
