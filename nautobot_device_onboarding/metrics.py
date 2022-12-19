"""Plugin additions to the Nautobot navigation menu."""
from prometheus_client import Counter

onboardingtask_results_counter = Counter(
    name="onboardingtask_results_total", documentation="Count of results for Onboarding Task", labelnames=("status",)
)
