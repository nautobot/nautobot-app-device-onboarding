"""Diffsync specific code."""
from collections import defaultdict
from diffsync.diff import Diff


class NetworkImporterDiff(Diff):
    """network_importer specific diff class based on diffsync."""

    @classmethod
    def order_children_interface(cls, children):  # pylint: disable=too-many-branches
        """Return the interface children ordered order."""
        intfs_lags = defaultdict(list)
        intfs_regs = defaultdict(list)
        intfs_lag_members = defaultdict(list)

        is_lag = []
        is_lag_members = []
        for child_name, child in children.items():
            if not child:
                continue
            if child.dest_attrs and child.dest_attrs.get("lag"):
                is_lag_members.append(child_name)
                is_lag.append(child.dest_attrs["lag"].split("__")[1])
            if child.source_attrs and child.source_attrs.get("lag"):
                is_lag_members.append(child_name)
                is_lag.append(child.source_attrs["lag"].split("__")[1])

        for child_name, child in children.items():
            action = child.action

            if action is None:
                action = "update"

            if action == "delete":
                if child_name in is_lag:
                    intfs_lags[action].append(child_name)
                elif child_name in is_lag_members:
                    intfs_lag_members[action].append(child_name)
                else:
                    intfs_regs[action].append(child_name)

            elif action in ["update", "create"]:

                if child_name in is_lag:
                    intfs_lags[action].append(child_name)
                elif child_name in is_lag_members:
                    intfs_lag_members[action].append(child_name)
                else:
                    intfs_regs[action].append(child_name)

            else:
                raise Exception("invalid DiffElement")

        sorted_intfs = intfs_regs["create"]
        sorted_intfs += intfs_regs["update"]
        sorted_intfs += intfs_lags["create"]
        sorted_intfs += intfs_lags["update"]
        sorted_intfs += intfs_lag_members["create"]
        sorted_intfs += intfs_lag_members["update"]
        sorted_intfs += intfs_regs["delete"]
        sorted_intfs += intfs_lags["delete"]
        sorted_intfs += intfs_lag_members["delete"]

        for intf in sorted_intfs:
            yield children[intf]
