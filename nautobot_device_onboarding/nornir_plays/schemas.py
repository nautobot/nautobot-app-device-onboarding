"""General Schemas and JSONSchemas for SSoT Based Sync Jobs."""


def sync_devices_schema(json_schema=True):
    """Schema for SSOTSyncDevices Job."""
    if json_schema:
        return {
            "title": "Sync Devices From Network",
            "description": "Schema for SSoT Sync Devices From Network",
            "type": "object",
            "required": ["hostname", "serial", "device_type", "mgmt_interface", "platform", "network_driver"],
            "properties": {
                "hostname": {"type": "string", "description": "Hostname of the network device"},
                "serial": {"type": "string", "description": "Serial number of the network device"},
                "device_type": {"type": "string", "description": "Type of the network device"},
                "mgmt_interface": {"type": "string", "description": "Management interface of the network device"},
                "mask_length": {
                    "type": "integer",
                    "default": 31,
                    "description": "Subnet mask length for the management interface (default: 31)",
                },
                "platform": {"type": "string", "description": "Platform of the network device"},
                "manufacturer": {
                    "type": "string",
                    "default": "PLACEHOLDER",
                    "description": "Manufacturer of the network device (default: PLACEHOLDER)",
                },
                "network_driver": {"type": "string", "description": "Network driver used for the device"},
            },
        }
    return {
        "hostname": "",
        "serial": "",
        "device_type": "",
        "mgmt_interface": "",
        "mask_length": 31,
        "platform": "",
        "manufacturer": "PLACEHOLDER",
        "network_driver": "",
    }


def sync_network_data_schema(json_schema=True):
    """Schema for SSoT SSOTSyncNetworkData."""
    if json_schema:
        return {
            "title": "Sync Network Data From Network",
            "description": "Schema for SSoT Sync Network Data From Network",
            "type": "object",
            "required": ["type", "ip_addresses", "mac_address", "link_status", "802.1Q_mode"],
            "properties": {
                "type": {"type": "string", "description": "Type of the network interface"},
                "ip_addresses": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["ip_address", "prefix_length"],
                        "properties": {
                            "ip_address": {"type": "string", "description": "IP address of the interface"},
                            "prefix_length": {"type": "integer", "description": "Prefix length of the IP address"},
                        },
                    },
                    "description": "List of IP addresses associated with the interface",
                },
                "mac_address": {"type": "string", "description": "MAC address of the interface"},
                "mtu": {"type": "string", "description": "MTU of the interface"},
                "description": {"type": "string", "description": "Description of the interface"},
                "link_status": {"type": "boolean", "description": "Link status of the interface (up or down)"},
                "802.1Q_mode": {"type": "string", "description": "802.1Q mode of the interface (access, trunk, etc.)"},
                "lag": {
                    "type": "string",
                    "description": "LAG (Link Aggregation Group) the interface belongs to (optional)",
                },
                "untagged_vlan": {"type": "object", "description": "Untagged VLAN information (optional)"},
                "tagged_vlans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "id"],
                        "properties": {
                            "name": {"type": "string", "description": "Name of the tagged VLAN"},
                            "id": {"type": "string", "description": "ID of the tagged VLAN"},
                        },
                    },
                    "description": "List of tagged VLANs associated with the interface (optional)",
                },
            },
        }
    return {
        "type": "str",
        "ip_addresses": [
            {"ip_address": "str", "prefix_length": "int"},
            {"ip_address": "str", "prefix_length": "int"},
        ],
        "mac_address": "str",
        "mtu": "str",
        "description": "str",
        "link_status": "bool",
        "802.1Q_mode": "str",
        "lag": "str",
        "untagged_vlan": "dict",
        "tagged_vlans": [{"name": "str", "id": "str"}, {"name": "str", "id": "str"}],
        "vrf": {"name": "str", "rd": "str"},
    }


NETWORK_DEVICES_SCHEMA = {
    "title": "Sync Device Data From Network",
    "description": "Schema for SSoT Sync Device Data From Network",
    "type": "object",
    "required": ["serial", "hostname", "device_type", "mgmt_interface", "mask_length"],
    "properties": {
        "serial": {
            "type": "string",
            "description": "Serial number of the network device",
            "minItems": 1,
        },
        "hostname": {"type": "string"},
        "device_type": {"type": "string"},
        "mgmt_interface": {"type": "string"},
        "mask_length": {"type": "integer"},
    },
}

NETWORK_DATA_SCHEMA = {
    "title": "Sync Network Data From Network",
    "description": "Schema for SSoT Sync Network Data From Network",
    "type": "object",
    "required": ["serial", "interfaces"],
    "properties": {
        "serial": {
            "type": "string",
            "description": "Serial number of the network device",
            "minItems": 1,
        },
        "interfaces": {
            "type": "object",
            "items": {
                "type": "object",
                "required": [
                    "type",
                    "ip_addresses",
                    "mac_address",
                    "mtu",
                    "description" "link_status",
                    "802.1Q_mode",
                ],
                "properties": {
                    "type": {"type": "string", "description": "Type of the network interface"},
                    "mac_address": {"type": "string", "description": "MAC address of the interface"},
                    "mtu": {"type": "string", "description": "MTU of the interface"},
                    "description": {"type": "string", "description": "Description of the interface"},
                    "link_status": {"type": "boolean", "description": "Link status of the interface (up or down)"},
                    "ip_addresses": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["ip_address", "prefix_length"],
                            "properties": {
                                "ip_address": {"type": "string", "description": "IP address of the interface"},
                                "prefix_length": {"type": "integer", "description": "Prefix length of the IP address"},
                            },
                        },
                        "description": "List of IP addresses associated with the interface",
                    },
                    "802.1Q_mode": {
                        "type": "string",
                        "description": "802.1Q mode of the interface (access, trunk, etc.)",
                    },
                    "lag": {
                        "type": "string",
                        "description": "LAG (Link Aggregation Group) the interface belongs to (optional)",
                    },
                    "tagged_vlans": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "id"],
                            "properties": {
                                "name": {"type": "string", "description": "Name of the tagged VLAN"},
                                "id": {"type": "string", "description": "ID of the tagged VLAN"},
                            },
                        },
                    },
                    "untagged_vlan": {"type": "object", "description": "Untagged VLAN information (optional)"},
                    "vrf": {"type": "object", "properties": {"name": {"type": "string"}, "rd": {"type": "string"}}},
                },
            },
        },
    },
}
