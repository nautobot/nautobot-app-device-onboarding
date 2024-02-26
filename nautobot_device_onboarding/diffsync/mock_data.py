"""Mock Data for use with Diffsync."""

# TODO: move this data to testing folder for use in tests

network_importer_mock_data = {
    "demo-cisco-xe1": {
        "serial": "9ABUXU581111",
        "interfaces": [
            {
                "GigabitEthernet1": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.1.8", "prefix_length": 16},
                    ],
                    "mac_address": "d8b1.905c.7130",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "tagged",
                    "lag": "",
                    "untagged_vlan": {"name": "vlan60", "id": "60"},
                    "tagged_vlans": [{"name": "vlan40", "id": "40"}],
                }
            },
            {
                "GigabitEthernet2": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.1.9", "prefix_length": 24},
                    ],
                    "mac_address": "d8b1.905c.7131",
                    "mtu": "1500",
                    "description": "uplink Po1",
                    "link_status": True,
                    "802.1Q_mode": "",
                    "lag": "Po2",
                    "untagged_vlan": "",
                    "tagged_vlans": [],
                }
            },
            {
                "GigabitEthernet3": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.1.10", "prefix_length": 24},
                        {"ip_address": "10.1.1.11", "prefix_length": 22},
                    ],
                    "mac_address": "d8b1.905c.7132",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "tagged",
                    "lag": "Po1",
                    "untagged_vlan": "",
                    "tagged_vlans": [{"name": "vlan40", "id": "40"}, {"name": "vlan50", "id": "50"}],
                }
            },
            {
                "GigabitEthernet4": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.1.12", "prefix_length": 20},
                    ],
                    "mac_address": "d8b1.905c.7133",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "",
                    "lag": "",
                    "untagged_vlan": "",
                    "tagged_vlans": [],
                }
            },
            {
                "Po1": {
                    "type": "lag",
                    "ip_addresses": [],
                    "mac_address": "d8b1.905c.7134",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "",
                    "lag": "",
                    "untagged_vlan": "",
                    "tagged_vlans": [],
                }
            },
            {
                "Po2": {
                    "type": "lag",
                    "ip_addresses": [],
                    "mac_address": "d8b1.905c.7135",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "",
                    "lag": "",
                    "untagged_vlan": "",
                    "tagged_vlans": [],
                }
            },
        ],
    },
    "demo-cisco-xe2": {
        "serial": "9ABUXU5882222",
        "interfaces": [
            {
                "GigabitEthernet1": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.2.8", "prefix_length": 24},
                    ],
                    "mac_address": "d8b1.905c.5170",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "tagged",
                    "lag": "",
                    "untagged_vlan": {"name": "vlan60", "id": "60"},
                    "tagged_vlans": [{"name": "vlan40", "id": "40"}],
                }
            },
            {
                "GigabitEthernet2": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.2.9", "prefix_length": 24},
                    ],
                    "mac_address": "d8b1.905c.5171",
                    "mtu": "1500",
                    "description": "uplink Po1",
                    "link_status": True,
                    "802.1Q_mode": "",
                    "lag": "Po1",
                    "untagged_vlan": "",
                    "tagged_vlans": [],
                }
            },
            {
                "GigabitEthernet3": {
                    "type": "100base-tx",
                    "ip_addresses": [
                        {"ip_address": "10.1.2.10", "prefix_length": 24},
                        {"ip_address": "10.1.2.11", "prefix_length": 22},
                    ],
                    "mac_address": "d8b1.905c.5172",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "tagged",
                    "lag": "Po1",
                    "untagged_vlan": "",
                    "tagged_vlans": [{"name": "vlan40", "id": "40"}, {"name": "vlan50", "id": "50"}],
                }
            },
            {
                "Po1": {
                    "type": "lag",
                    "ip_addresses": [],
                    "mac_address": "d8b1.905c.5173",
                    "mtu": "1500",
                    "description": "",
                    "link_status": True,
                    "802.1Q_mode": "",
                    "lag": "",
                    "untagged_vlan": "",
                    "tagged_vlans": [],
                }
            },
        ],
    },
}

device_onboarding_mock_data = {
    "10.1.1.11": {
        "hostname": "demo-cisco-xe1",
        "serial": "9ABUXU581111",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "IOS-test",
        "network_driver": "cisco_ios",
        "mask_length": 16,
    },
    "10.1.1.10": {
        "hostname": "demo-cisco-xe2",
        "serial": "9ABUXU5882222",
        "device_type": "CSR1000V2",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "IOS",
        "network_driver": "cisco_ios",
        "mask_length": 24,
    },
}
