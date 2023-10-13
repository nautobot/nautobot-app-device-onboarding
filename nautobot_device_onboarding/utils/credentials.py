"""User credentials helper module for device onboarding."""


class Credentials:
    """Class used to hide user's credentials in RQ worker and Django."""

    def __init__(self, username=None, password=None, secret=None):
        """Create a Credentials instance."""
        self.username = username
        self.password = password
        self.secret = secret

    def __repr__(self):
        """Return string representation of a Credentials object."""
        return "*Credentials argument hidden*"

    def nautobot_serialize(self):
        """Serialize object for Celery."""
        return {
            "username": self.username,
            "password": self.password,
            "secret": self.secret,
        }

    @classmethod
    def nautobot_deserialize(cls, data):
        """Deserialize object for Celery."""
        return cls(
            username=data["username"],
            password=data["password"],
            secret=data["secret"],
        )


def onboarding_credentials_serializer(credentials):
    """Serialize object for Celery."""
    return {
        "username": credentials.username,
        "password": credentials.password,
        "secret": credentials.secret,
    }
