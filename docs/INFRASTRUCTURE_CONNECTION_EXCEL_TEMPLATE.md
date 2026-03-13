# Infrastructure Connection Excel Import Template

## Required Columns

Your Excel file **must** include these three columns (column names are case-insensitive):

1. **name** (or any of: `hostname`, `device_name`, `device`, `connection_name`)
2. **target_host** (or any of: `host`, `ip`, `ip_address`, `mgmt_ip`, `address`, `management_ip`)
3. **connection_type** (or any of: `type`, `connector_type`, `device_type`, `device_category`)

## Optional Columns

- `target_port` (or `port`, `ssh_port`, `mgmt_port`, `management_port`)
- `environment` (or `env`, `stage`) - defaults to "prod"
- `username` (or `user`, `login`)
- `password` (or `pass`, `pwd`)

### For Network Devices Only

- `vendor` (or `manufacturer`, `brand`)
- `model` (or `model_number`, `device_model`)
- `device_type` (or `device_category`, `category`)
- `location` (or `site_location`, `physical_location`)
- `network_segment` (or `segment`, `vlan`, `network`)
- `site` (or `datacenter`, `dc`, `facility`)
- `serial_number` (or `serial`, `sn`)
- `firmware_version` (or `firmware`, `os_version`, `version`)
- `snmp_community` (or `community`, `snmp_read`)
- `snmp_version` (or `snmp_ver`)

## Valid Connection Types

- `ssh`
- `winrm`
- `database`
- `api`
- `network_device`
- `aws_ssm`
- `azure_bastion`

## Example Excel Format

| name | target_host | connection_type | target_port | environment | username | password |
|------|-------------|-----------------|-------------|-------------|----------|----------|
| Web Server 1 | 192.168.1.10 | ssh | 22 | prod | admin | password123 |
| Database Server | 192.168.1.20 | database | 5432 | prod | dbuser | dbpass |
| Router Main | 192.168.1.1 | network_device | 22 | prod | admin | routerpass |

## Common Issues

1. **"No valid connections found"**
   - Make sure all required columns are present (name, target_host, connection_type)
   - Ensure rows are not completely empty
   - Check that required fields have values (not blank)

2. **"Missing required columns"**
   - Verify column names match exactly (case-insensitive)
   - Check for extra spaces in column names
   - Use one of the accepted aliases listed above

3. **Rows being skipped**
   - Ensure name, target_host, and connection_type fields are filled in
   - Remove completely empty rows
   - Check for special characters that might cause issues

## Tips

- Column names are case-insensitive: `Name`, `NAME`, `name` all work
- Extra whitespace is automatically trimmed
- Empty rows are automatically skipped
- If `connection_type` is not recognized, it defaults to `ssh`
- For network devices, you can use device types like "router", "switch", "firewall" - they'll be mapped to `network_device`
