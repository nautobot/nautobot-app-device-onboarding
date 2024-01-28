def format_ob_data_ios(host, result):
    """Format the data for onboarding IOS devices."""
    primary_ip4 = host.name
    formatted_data = {}

    for r in result:
        if r.name == "show inventory":
            device_type = r.result[0].get("pid")
            formatted_data["device_type"] = device_type
        elif r.name == "show version":
            hostname = r.result[0].get("hostname")
            serial = r.result[0].get("serial")
            formatted_data["hostname"] = hostname
            formatted_data["serial"] = serial[0]
        elif r.name == "show interfaces":
            show_interfaces = r.result
            for interface in show_interfaces:
                if interface.get("ip_address") == primary_ip4:
                    mask_length = interface.get("prefix_length")
                    interface_name = interface.get("interface")
                    formatted_data["mask_length"] = mask_length
                    formatted_data["mgmt_interface"] = interface_name

    return formatted_data


def format_ob_data_nxos(host, result):
    """Format the data for onboarding NXOS devices."""
    primary_ip4 = host.name
    formatted_data = {}

    for r in result:
        if r.name == "show inventory":
            # TODO: Add check for PID when textfsm template is fixed
            pass
        elif r.name == "show version":
            device_type = r.result[0].get("platform")
            formatted_data["device_type"] = device_type
            hostname = r.result[0].get("hostname")
            serial = r.result[0].get("serial")
            formatted_data["hostname"] = hostname
            if serial:
                formatted_data["serial"] = serial
            else:
                formatted_data["serial"] = ""
        elif r.name == "show interface":
            show_interfaces = r.result
            print(f"show interfaces {show_interfaces}")
            for interface in show_interfaces:
                if interface.get("ip_address") == primary_ip4:
                    mask_length = interface.get("prefix_length")
                    interface_name = interface.get("interface")
                    formatted_data["mask_length"] = mask_length
                    formatted_data["mgmt_interface"] = interface_name
                    break

    return formatted_data
