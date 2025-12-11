"""
Excel importer for Infrastructure Connections
Supports bulk import of network devices, servers, databases, etc. from Excel files
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from io import BytesIO
from app.core.logging import get_logger

logger = get_logger(__name__)


class InfrastructureConnectionExcelImporter:
    """Import infrastructure connections from Excel files"""
    
    # Expected column names (case-insensitive, flexible mapping)
    REQUIRED_COLUMNS = {
        'name': ['name', 'hostname', 'device_name', 'device', 'connection_name'],
        'target_host': ['target_host', 'host', 'ip', 'ip_address', 'mgmt_ip', 'address', 'management_ip'],
        'connection_type': ['connection_type', 'type', 'connector_type', 'device_type', 'device_category'],
    }
    
    OPTIONAL_COLUMNS = {
        'target_port': ['target_port', 'port', 'ssh_port', 'mgmt_port', 'management_port'],
        'target_service': ['target_service', 'service', 'service_name'],
        'environment': ['environment', 'env', 'stage'],
        'username': ['username', 'user', 'login'],
        'password': ['password', 'pass', 'pwd'],
        # Network device specific (stored in meta_data)
        'vendor': ['vendor', 'manufacturer', 'brand'],
        'model': ['model', 'model_number', 'device_model'],
        'device_type': ['device_type', 'device_category', 'category'],
        'location': ['location', 'site_location', 'physical_location'],
        'network_segment': ['network_segment', 'segment', 'vlan', 'network'],
        'site': ['site', 'datacenter', 'dc', 'facility'],
        'serial_number': ['serial_number', 'serial', 'sn'],
        'firmware_version': ['firmware_version', 'firmware', 'os_version', 'version'],
        'snmp_community': ['snmp_community', 'community', 'snmp_read'],
        'snmp_version': ['snmp_version', 'snmp_ver'],
    }
    
    CONNECTION_TYPES = ['ssh', 'winrm', 'database', 'api', 'network_device', 'aws_ssm', 'azure_bastion']
    
    def __init__(self):
        self.name = "infrastructure_connection_excel_importer"
    
    def parse_excel(self, file_content: bytes, filename: str = "import.xlsx") -> List[Dict[str, Any]]:
        """
        Parse Excel file and extract infrastructure connection information
        
        Args:
            file_content: Excel file content as bytes
            filename: Original filename (for error messages)
        
        Returns:
            List of connection dictionaries ready for database insertion
        """
        try:
            # Read Excel file
            df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
            
            if df.empty:
                raise ValueError("Excel file is empty")
            
            # Normalize column names (lowercase, strip whitespace)
            df.columns = df.columns.str.lower().str.strip()
            
            # Map columns to our expected names
            column_mapping = self._map_columns(df.columns.tolist())
            
            # Validate required columns
            missing_required = []
            for required_name, possible_names in self.REQUIRED_COLUMNS.items():
                if required_name not in column_mapping.values():
                    missing_required.append(required_name)
            
            if missing_required:
                raise ValueError(
                    f"Missing required columns: {', '.join(missing_required)}. "
                    f"Found columns: {', '.join(df.columns.tolist())}"
                )
            
            # Extract connections
            connections = []
            for idx, row in df.iterrows():
                try:
                    connection = self._extract_connection(row, column_mapping, idx + 2)  # +2 for header and 0-index
                    if connection:
                        connections.append(connection)
                except Exception as e:
                    logger.warning(f"Error parsing row {idx + 2}: {e}")
                    continue
            
            if not connections:
                raise ValueError("No valid connections found in Excel file")
            
            logger.info(f"Successfully parsed {len(connections)} infrastructure connections from Excel")
            return connections
            
        except pd.errors.EmptyDataError:
            raise ValueError("Excel file is empty or invalid")
        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}", exc_info=True)
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map Excel column names to our expected field names"""
        mapping = {}
        
        # Map required columns
        for expected_name, possible_names in self.REQUIRED_COLUMNS.items():
            for col in columns:
                if col in possible_names:
                    mapping[col] = expected_name
                    break
        
        # Map optional columns
        for expected_name, possible_names in self.OPTIONAL_COLUMNS.items():
            for col in columns:
                if col in possible_names and col not in mapping:
                    mapping[col] = expected_name
                    break
        
        return mapping
    
    def _extract_connection(self, row: pd.Series, column_mapping: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Extract connection information from a single row"""
        # Get column name for each expected field
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        
        # Required fields
        name = self._get_value(row, reverse_mapping.get('name'))
        target_host = self._get_value(row, reverse_mapping.get('target_host'))
        connection_type = self._get_value(row, reverse_mapping.get('connection_type'))
        
        if not name or not target_host or not connection_type:
            raise ValueError(f"Row {row_num}: Missing required fields (name, target_host, connection_type)")
        
        # Normalize connection type
        connection_type = connection_type.lower().strip()
        
        # Map device_type to connection_type if needed (for network devices)
        device_type = self._get_value(row, reverse_mapping.get('device_type'))
        if device_type and connection_type not in self.CONNECTION_TYPES:
            # If connection_type is a device type, map it
            device_type_lower = str(device_type).lower().strip()
            if device_type_lower in ['router', 'switch', 'firewall', 'load_balancer', 'access_point']:
                connection_type = 'network_device'
        
        # If still not a valid connection type, default based on context
        if connection_type not in self.CONNECTION_TYPES:
            # Try to infer from other fields
            if 'network' in connection_type or device_type:
                connection_type = 'network_device'
            elif 'database' in connection_type or 'db' in connection_type:
                connection_type = 'database'
            elif 'api' in connection_type:
                connection_type = 'api'
            else:
                connection_type = 'ssh'  # Default to SSH
        
        # Build connection dictionary
        connection = {
            'name': str(name).strip(),
            'target_host': str(target_host).strip(),
            'connection_type': connection_type,
        }
        
        # Optional fields
        for field_name in ['target_port', 'target_service', 'environment']:
            col_name = reverse_mapping.get(field_name)
            if col_name:
                value = self._get_value(row, col_name)
                if value is not None and str(value).strip():
                    if field_name == 'target_port':
                        try:
                            connection[field_name] = int(value)
                        except (ValueError, TypeError):
                            connection[field_name] = 22 if connection_type == 'ssh' else None
                    else:
                        connection[field_name] = str(value).strip()
        
        # Defaults
        if 'target_port' not in connection:
            connection['target_port'] = 22 if connection_type == 'ssh' else None
        if 'environment' not in connection:
            connection['environment'] = 'prod'
        
        # Handle credentials (username/password from Excel)
        if 'username' in reverse_mapping or 'password' in reverse_mapping:
            connection['_credentials'] = {
                'username': self._get_value(row, reverse_mapping.get('username')),
                'password': self._get_value(row, reverse_mapping.get('password')),
            }
        
        # Network device metadata (stored in meta_data)
        if connection_type == 'network_device':
            meta_data = {}
            for field_name in ['vendor', 'model', 'device_type', 'location', 'network_segment', 
                             'site', 'serial_number', 'firmware_version', 'snmp_community', 'snmp_version']:
                col_name = reverse_mapping.get(field_name)
                if col_name:
                    value = self._get_value(row, col_name)
                    if value is not None and str(value).strip():
                        meta_data[field_name] = str(value).strip()
            
            if meta_data:
                connection['meta_data'] = meta_data
        
        return connection
    
    def _get_value(self, row: pd.Series, column_name: Optional[str]) -> Optional[Any]:
        """Safely get value from row, handling NaN"""
        if not column_name or column_name not in row:
            return None
        value = row[column_name]
        if pd.isna(value):
            return None
        return value









