from django.db import migrations, models


def create_labels_for_existing_tasks(apps, schema_editor):
    OnboardingTask = apps.get_model("nautobot_device_onboarding", "OnboardingTask")

    for index, task_object in enumerate(OnboardingTask.objects.order_by("created"), start=1):
        task_object.label = index
        task_object.save()


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0002_create_onboardingdevice"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingtask",
            name="label",
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.RunPython(create_labels_for_existing_tasks, migrations.RunPython.noop),
    ]
