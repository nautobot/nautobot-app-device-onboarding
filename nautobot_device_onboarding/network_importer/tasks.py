"""Collection of Nornir tasks for the network importer."""

import logging
import socket
from typing import Optional, List

from nornir.core.task import Result, Task

LOGGER = logging.getLogger("network-importer")  # pylint: disable=C0103


def tcp_ping(task: Task, ports: List[int], timeout: int = 2, host: Optional[str] = None) -> Result:
    """Tests connection to a tcp port and tries to establish a three way handshake.

    Arguments:
        ports (list of int): tcp ports to ping
        timeout (int, optional): defaults to 2
        host (string, optional): defaults to ``hostname``

    Returns:
        Result object with the following attributes set:
          * result (``dict``): Contains port numbers as keys with True/False as values

    Code copied from https://github.com/nornir-automation/nornir/blob/v2.5.0/nornir/plugins/tasks/networking/tcp_ping.py
    Need to open a PR to https://github.com/nornir-automation/nornir_utils
    """
    if isinstance(ports, int):
        ports = [ports]

    if isinstance(ports, list):
        if not all(isinstance(port, int) for port in ports):
            raise ValueError("Invalid value for 'ports'")

    else:
        raise ValueError("Invalid value for 'ports'")

    host = host or task.host.hostname

    result = {}
    for port in ports:
        skt = socket.socket()
        skt.settimeout(timeout)
        try:
            status = skt.connect_ex((host, port))
            if status == 0:  # pylint: disable=simplifiable-if-statement
                connection = True
            else:
                connection = False
        except (socket.gaierror, socket.timeout, socket.error):
            connection = False
        finally:
            skt.close()
        result[port] = connection

    return Result(host=task.host, result=result)


def check_if_reachable(task: Task) -> Result:
    """Check if a device is reachable by doing a TCP ping it on port 22.

    Will change the status of the variable `host.is_reachable` based on the results

    Args:
      task: Nornir Task

    Returns:
       Result: Nornir Result
    """
    port_to_check = 22
    try:
        results = task.run(task=tcp_ping, ports=[port_to_check])
    except:  # noqa: E722 # pylint: disable=bare-except
        LOGGER.debug(
            "An exception occured while running the reachability test (tcp_ping)",
            exc_info=True,
        )
        return Result(host=task.host, failed=True)

    is_reachable = results[0].result[port_to_check]

    if not is_reachable:
        LOGGER.debug("%s | device is not reachable on port %s", task.host.name, port_to_check)
        task.host.is_reachable = False
        task.host.not_reachable_reason = f"device not reachable on port {port_to_check}"
        task.host.status = "fail-ip"

    return Result(host=task.host, result=is_reachable)


def warning_not_reachable(task: Task) -> Result:
    """Generate warning logs for each unreachable device."""
    if task.host.is_reachable:
        return

    reason = task.host.not_reachable_reason or "reason not defined"
    LOGGER.warning("%s device is not reachable, %s", task.host.name, reason)
