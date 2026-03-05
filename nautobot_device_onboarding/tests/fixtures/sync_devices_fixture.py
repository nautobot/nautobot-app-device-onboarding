"""Data fixture for use in testing."""

sync_devices_mock_data_single_device_valid = {
    "10.1.1.10": {
        "hostname": "test device 1",
        "serial": "test-serial-abc",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_nxos",
        "network_driver": "cisco_nxos",
        "mask_length": 24,
    },
}
sync_devices_mock_data_single_device_alternate_valid = {
    "192.1.1.10": {
        "hostname": "test device 1",
        "serial": "test-serial-abc",
        "device_type": "CSR1000V17",
        "mgmt_interface": "NewInterfaceName",
        "manufacturer": "Cisco",
        "platform": "cisco_nxos",
        "network_driver": "cisco_nxos",
        "mask_length": 24,
    },
}

sync_devices_mock_data_valid = {
    "10.1.1.10": {
        "hostname": "demo-cisco-1",
        "serial": "9ABUXU5882222",
        "device_type": "CSR1000V2",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_ios",
        "network_driver": "cisco_ios",
        "mask_length": 24,
    },
    "10.1.1.11": {
        "hostname": "demo-cisco-2",
        "serial": "9ABUXU581111",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_ios",
        "network_driver": "cisco_ios",
        "mask_length": 16,
    },
}

sync_devices_mock_data_invalid = {
    "10.1.1.10": {
        "hostname": "demo-cisco-1",
        "serial": "",
        "device_type": "CSR1000V2",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_ios",
        "network_driver": "cisco_ios",
        "mask_length": 24,
    },
    "10.1.1.11": {
        "hostname": "demo-cisco-2",
        "serial": "9ABUXU581111",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_xe",
        "network_driver": "cisco_xe",
        "mask_length": 16,
    },
}

sync_devices_data_update = {
    "10.1.1.10": {
        "hostname": "test device 1",
        "serial": "9ABUXU5882222",
        "device_type": "Test model 2",
        "mgmt_interface": "NewInterfaceName",
        "manufacturer": "Cisco",
        "platform": "cisco_xe",
        "network_driver": "cisco_xe",
        "mask_length": 24,
    },
}

# Virtual Chassis / Switch Stack test data
sync_devices_mock_data_virtual_chassis = {
    "10.1.1.20": {
        "hostname": "stack-switch-1",
        "serial": "STACK001",
        "device_type": "C9300-48P",
        "mgmt_interface": "Vlan1",
        "manufacturer": "Cisco",
        "platform": "cisco_xe",
        "network_driver": "cisco_xe",
        "mask_length": 24,
        "virtual_chassis": [
            {"switch": "1", "priority": "15"},
            {"switch": "2", "priority": "14"},
            {"switch": "3", "priority": "1"},
        ],
        "modules": [
            {"model": "C9300-48P", "serial": "STACK001"},
            {"model": "C9300-24P", "serial": "STACK002"},
            {"model": "C9300-48P", "serial": "STACK003"},
        ],
    },
}

# Standalone device (not part of a switch stack) - explicit empty/single virtual_chassis
sync_devices_mock_data_standalone = {
    "10.1.1.21": {
        "hostname": "standalone-switch-1",
        "serial": "STANDALONE001",
        "device_type": "C9300-48P",
        "mgmt_interface": "Vlan1",
        "manufacturer": "Cisco",
        "platform": "cisco_xe",
        "network_driver": "cisco_xe",
        "mask_length": 24,
        "virtual_chassis": [
            {"switch": "1", "priority": "15"},
        ],
        "modules": [
            {"model": "C9300-48P", "serial": "STANDALONE001"},
        ],
    },
}
