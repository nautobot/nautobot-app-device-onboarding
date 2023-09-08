"""Worker code for processing inbound OnboardingTasks."""
import logging

from django.core.exceptions import ValidationError
from prometheus_client import Summary

from nautobot.dcim.models import Device

from nautobot_device_onboarding.utils.credentials import Credentials
from nautobot_device_onboarding.choices import OnboardingFailChoices
from nautobot_device_onboarding.choices import OnboardingStatusChoices
from nautobot_device_onboarding.exceptions import OnboardException
from nautobot_device_onboarding.helpers import onboarding_task_fqdn_to_ip
from nautobot_device_onboarding.metrics import onboardingtask_results_counter
from nautobot_device_onboarding.models import OnboardingDevice
from nautobot_device_onboarding.models import OnboardingTask
from nautobot_device_onboarding.onboard import OnboardingManager

logger = logging.getLogger("rq.worker")


REQUEST_TIME = Summary("onboardingtask_processing_seconds", "Time spent processing onboarding request")


try:
    from nautobot.core.celery import nautobot_task  # pylint: disable=ungrouped-imports

    CELERY_WORKER = True

    @nautobot_task
    def onboard_device_worker(task_id, credentials):
        """Onboard device with Celery worker."""
        return onboard_device(task_id=task_id, credentials=credentials)

except ImportError:
    logger.info("INFO: Celery was not found - using Django RQ Worker")

    CELERY_WORKER = False

    from django_rq import get_queue

    def onboard_device_worker(task_id, credentials):
        """Onboard device with RQ worker."""
        return onboard_device(task_id=task_id, credentials=credentials)


@REQUEST_TIME.time()
def onboard_device(task_id, credentials):  # pylint: disable=too-many-statements, too-many-branches
    """Process a single OnboardingTask instance."""
    credentials = Credentials.nautobot_deserialize(credentials)
    username = credentials.username
    password = credentials.password
    secret = credentials.secret

    onboarding_task = OnboardingTask.objects.get(id=task_id)

    # Rewrite FQDN to IP for Onboarding Task
    onboarding_task_fqdn_to_ip(onboarding_task)

    logger.info("START: onboard device")
    onboarded_device = None

    try:
        try:
            if onboarding_task.ip_address:
                onboarded_device = Device.objects.get(primary_ip4__host=onboarding_task.ip_address)

            if OnboardingDevice.objects.filter(device=onboarded_device, enabled=False):
                onboarding_task.status = OnboardingStatusChoices.STATUS_SKIPPED

                return {"onboarding_task": True}

        except Device.DoesNotExist as err:
            logger.info("Getting device with IP lookup failed: %s", str(err))
        except Device.MultipleObjectsReturned as err:
            logger.info("Getting device with IP lookup failed: %s", str(err))
            raise OnboardException(
                reason="fail-general", message=f"ERROR Multiple devices exist for IP {onboarding_task.ip_address}"
            ) from err
        except ValueError as err:
            logger.info("Getting device with IP lookup failed: %s", str(err))
        except ValidationError as err:
            logger.info("Getting device with IP lookup failed: %s", str(err))

        onboarding_task.status = OnboardingStatusChoices.STATUS_RUNNING
        onboarding_task.save()

        onboarding_manager = OnboardingManager(
            onboarding_task=onboarding_task, username=username, password=password, secret=secret
        )

        if onboarding_manager.created_device:
            onboarding_task.created_device = onboarding_manager.created_device

        onboarding_task.status = OnboardingStatusChoices.STATUS_SUCCEEDED
        onboarding_task.save()
        logger.info("FINISH: onboard device")
        onboarding_status = True

    except OnboardException as err:
        if onboarded_device:
            onboarding_task.created_device = onboarded_device

        logger.error("%s", err)
        onboarding_task.status = OnboardingStatusChoices.STATUS_FAILED
        onboarding_task.failed_reason = err.reason
        onboarding_task.message = err.message
        onboarding_task.save()
        onboarding_status = False

    except Exception as err:  # pylint: disable=broad-except
        if onboarded_device:
            onboarding_task.created_device = onboarded_device

        logger.error("Onboarding Error - Exception")
        logger.error(str(err))
        onboarding_task.status = OnboardingStatusChoices.STATUS_FAILED
        onboarding_task.failed_reason = OnboardingFailChoices.FAIL_GENERAL
        onboarding_task.message = str(err)
        onboarding_task.save()
        onboarding_status = False

    finally:
        if onboarded_device and not OnboardingDevice.objects.filter(device=onboarded_device):
            OnboardingDevice.objects.create(device=onboarded_device)

    onboardingtask_results_counter.labels(status=onboarding_task.status).inc()

    return {"ok": onboarding_status}


def enqueue_onboarding_task(task_id, credentials):
    """Detect worker type and enqueue task."""
    if CELERY_WORKER:
        onboard_device_worker.delay(task_id, credentials.nautobot_serialize())  # pylint: disable=no-member

    if not CELERY_WORKER:
        get_queue("default").enqueue(  # pylint: disable=used-before-assignment
            "nautobot_device_onboarding.worker.onboard_device_worker", task_id, credentials
        )
