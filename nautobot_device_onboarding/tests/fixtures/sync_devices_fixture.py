"""Data fixture for use in testing."""

sync_devices_mock_data_valid = {
    "10.1.1.10": {
        "hostname": "demo-cisco-ios",
        "serial": "9ABUXU5882222",
        "device_type": "CSR1000V2",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_ios",
        "network_driver": "cisco_ios",
        "mask_length": 24,
    },
    "10.1.1.11": {
        "hostname": "demo-cisco-xe",
        "serial": "9ABUXU581111",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_xe",
        "network_driver": "cisco_xe",
        "mask_length": 16,
    },
}

sync_devices_mock_data_invalid = {
    "10.1.1.10": {
        "hostname": "demo-cisco-ios",
        "serial": "",
        "device_type": "CSR1000V2",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_ios",
        "network_driver": "cisco_ios",
        "mask_length": 24,
    },
    "10.1.1.11": {
        "hostname": "demo-cisco-xe",
        "serial": "9ABUXU581111",
        "device_type": "CSR1000V17",
        "mgmt_interface": "GigabitEthernet1",
        "manufacturer": "Cisco",
        "platform": "cisco_xe",
        "network_driver": "cisco_xe",
        "mask_length": 16,
    },
}
