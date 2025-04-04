"""Choices used througout the app."""

SSOT_JOB_TO_COMMAND_CHOICE = (
    ("sync_devices", "Sync Devices"),
    ("sync_network_data", "Sync Network Data"),
    ("both", "Both"),
)


class AutodiscoveryProtocolTypeChoices(ChoiceSet):
    """Auto Discovery Protocol Type Choices."""

    SSH = "ssh"

    CHOICES = (
        (SSH, "ssh"),
    )

    AUTODISCOVERY_PORTS = (
        (SSH, [22]),
    )
