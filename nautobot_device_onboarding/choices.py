"""Choices used througout the app."""
from nautobot.core.choices import ChoiceSet


SSOT_JOB_TO_COMMAND_CHOICE = (
    ("sync_devices", "Sync Devices"),
    ("sync_network_data", "Sync Network Data"),
    ("both", "Both"),
)

class VLANLocationSyncTypeChoices(ChoiceSet):
    SINGLE_LOCATION = "single_location"
    MULTIPLE_LOCATION = "multiple_location"

    CHOICES = (
        (SINGLE_LOCATION, "Single Location"),
        (MULTIPLE_LOCATION, "Multiple Location"),
    )