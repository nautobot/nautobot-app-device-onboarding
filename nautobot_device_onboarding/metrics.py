"""Plugin metrics."""

from prometheus_client import Counter

from prometheus_client.metrics_core import GaugeMetricFamily

from nautobot_device_onboarding.choices import OnboardingStatusChoices, OnboardingFailChoices
from nautobot_device_onboarding.models import OnboardingTask

METRICS_PREFIX = "deviceonboarding_"

"""Used in the worker to keep track of total onboarding tasks.
"""
onboardingtask_results_counter = Counter(
    name="onboardingtask_results_total", documentation="Count of results for Onboarding Task", labelnames=("status",)
)


def current_onboarding_results():
    """Creates a gauge metric for Onboarding Task Results."""
    results_gauges = GaugeMetricFamily(
        f"{METRICS_PREFIX}onboardtask_results_count", "Device Onboarding Task Results", labels=["status"]
    )

    results_gauges.add_metric(labels=["total"], value=OnboardingTask.objects.count())
    for status_choice in OnboardingStatusChoices.CHOICES:
        results_gauges.add_metric(
            labels=[status_choice[0]], value=OnboardingTask.objects.filter(status=status_choice[0]).count()
        )

    yield results_gauges


def current_onboarding_failures():
    """Creates a gauge metric for Onboarding Task failures.

    This only shows the failures, so if none have failed or failures have been deleted, this will return 0.
    Metric labels are the failure reason.
    """
    results_gauges = GaugeMetricFamily(
        f"{METRICS_PREFIX}onboardtask_failure_count", "Device Onboarding Failures", labels=["failure_code"]
    )

    for failure_choice in OnboardingFailChoices.CHOICES:
        results_gauges.add_metric(
            labels=[failure_choice[0]], value=OnboardingTask.objects.filter(failed_reason=failure_choice[0]).count()
        )

    yield results_gauges


metrics = [current_onboarding_results, current_onboarding_failures]
