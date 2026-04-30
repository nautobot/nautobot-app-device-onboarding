"""Standalone maintenance job to backfill VRF-to-Prefix associations.

Self-contained: can be delivered via a Nautobot Git repository job source,
or left in this app package and discovered by Nautobot's built-in job loader.
No imports from the rest of this app are required.
"""

from django.db.models import Prefetch
from nautobot.apps.jobs import BooleanVar, DryRunVar, Job, MultiObjectVar, register_jobs
from nautobot.ipam.models import VRF, IPAddress, Namespace

name = "Device Onboarding Maintenance"


class AssociateVRFsToPrefixes(Job):
    """Associate each interface's VRF with the parent Prefix of the interface's IP addresses.

    Walks existing Interface VRF assignments and additively tags parent Prefixes with the VRF.
    Useful for backfilling data on deployments that ran historical syncs without the
    'Sync VRF to Prefix' toggle enabled.

    Additive-only: existing Prefix-to-VRF associations are never removed. A single run only
    observes currently-assigned interfaces, so absence of an interface for a VRF cannot be
    interpreted as a signal to unlink.
    """

    class Meta:
        """Job metadata."""

        name = "Associate VRFs with Prefixes"
        description = (
            "Backfill Prefix-to-VRF associations from existing Interface VRF assignments. "
            "Additive-only; never removes existing associations."
        )
        has_sensitive_variables = False

    dryrun = DryRunVar()
    debug = BooleanVar(default=False, description="Enable verbose logging.")
    namespaces = MultiObjectVar(
        model=Namespace,
        required=False,
        description="Limit to these Namespaces. If blank, all Namespaces are considered.",
    )
    vrfs = MultiObjectVar(
        model=VRF,
        required=False,
        query_params={"namespace": "$namespaces"},
        description=(
            "Limit to these VRFs. If blank, all VRFs in scope are considered. "
            "Choices are filtered by the selected Namespaces when one or more are chosen."
        ),
    )

    def run(self, dryrun, debug, namespaces=None, vrfs=None):  # pylint: disable=arguments-differ
        """Execute the backfill."""
        vrf_queryset = VRF.objects.select_related("namespace")
        if namespaces:
            vrf_queryset = vrf_queryset.filter(namespace__in=namespaces)
        if vrfs:
            vrf_queryset = vrf_queryset.filter(pk__in=[vrf.pk for vrf in vrfs])

        stats = {
            "linked": 0,
            "already_linked": 0,
            "skipped_no_parent": 0,
            "skipped_namespace_mismatch": 0,
        }

        for vrf in vrf_queryset.iterator():
            interface_queryset = vrf.interfaces.prefetch_related(
                Prefetch("ip_addresses", queryset=IPAddress.objects.select_related("parent"))
            )
            for interface in interface_queryset:
                for ip_address in interface.ip_addresses.all():
                    self._process_ip(vrf, interface, ip_address, stats, dryrun=dryrun, debug=debug)

        prefix = "[DRY RUN] " if dryrun else ""
        self.logger.info(
            "%sLinked: %d, already linked: %d, skipped (no parent prefix): %d, " "skipped (namespace mismatch): %d",
            prefix,
            stats["linked"],
            stats["already_linked"],
            stats["skipped_no_parent"],
            stats["skipped_namespace_mismatch"],
        )
        return stats

    def _process_ip(self, vrf, interface, ip_address, stats, *, dryrun, debug):
        """Link a single IP's parent Prefix to the VRF if eligible."""
        parent = ip_address.parent
        if parent is None:
            stats["skipped_no_parent"] += 1
            if debug:
                self.logger.debug(
                    "Skipped %s on interface [%s] (device [%s]): no parent prefix",
                    ip_address,
                    interface,
                    interface.parent,
                )
            return

        if parent.namespace_id != vrf.namespace_id:
            stats["skipped_namespace_mismatch"] += 1
            self.logger.warning(
                "Skipped prefix [%s] (namespace [%s]) for vrf [%s] (namespace [%s]): "
                "namespaces must match for VRF assignment.",
                parent,
                parent.namespace,
                vrf,
                vrf.namespace,
            )
            return

        if parent.vrfs.filter(pk=vrf.pk).exists():
            stats["already_linked"] += 1
            return

        if not dryrun:
            parent.vrfs.add(vrf)
        stats["linked"] += 1
        self.logger.info(
            "%sLinked vrf [%s] to prefix [%s] via interface [%s] on device [%s].",
            "[DRY RUN] " if dryrun else "",
            vrf,
            parent,
            interface,
            interface.parent,
        )


register_jobs(AssociateVRFsToPrefixes)
