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
