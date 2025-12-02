"""
Network Device Execution Engine
Handles SSH/Telnet/API connections to network devices (Cisco, Juniper, etc.)
Supports config backup and rollback
"""
import asyncio
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class NetworkDeviceExecutor:
    """Execute commands on network devices via SSH/Telnet/API"""
    
    def __init__(self):
        self.name = "network_device_executor"
    
    async def execute_command(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Execute a command on a network device
        
        Args:
            device: Network device info (management_ip, connection_protocol, vendor, model)
            command: Command to execute
            credential: Credential info (username, password)
            timeout: Command timeout in seconds
        
        Returns:
            Dict with 'success', 'output', 'error', 'exit_code'
        """
        try:
            protocol = device.get('connection_protocol', 'ssh').lower()
            vendor = (device.get('vendor') or '').lower()
            
            if protocol == 'ssh':
                return await self._execute_ssh(device, command, credential, timeout, vendor)
            elif protocol == 'telnet':
                return await self._execute_telnet(device, command, credential, timeout, vendor)
            elif protocol == 'api':
                return await self._execute_api(device, command, credential, timeout, vendor)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported protocol: {protocol}',
                    'output': '',
                    'exit_code': 1
                }
        except Exception as e:
            logger.error(f"Error executing command on network device: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'exit_code': 1
            }
    
    async def _execute_ssh(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]],
        timeout: int,
        vendor: str
    ) -> Dict[str, Any]:
        """Execute command via SSH (using paramiko or asyncssh)"""
        # TODO: Implement actual SSH connection using asyncssh or paramiko
        # For now, return a placeholder that indicates SSH execution
        
        management_ip = device.get('management_ip')
        port = device.get('management_port', 22)
        username = credential.get('username') if credential else None
        password = credential.get('password') if credential else None
        
        if not username or not password:
            return {
                'success': False,
                'error': 'SSH credentials (username/password) required',
                'output': '',
                'exit_code': 1
            }
        
        # Vendor-specific command formatting
        formatted_command = self._format_command_for_vendor(command, vendor, device)
        
        logger.info(
            f"Executing SSH command on {management_ip}:{port} "
            f"(vendor={vendor}, command={formatted_command[:50]}...)"
        )
        
        # Placeholder - actual implementation would use asyncssh
        # For now, return success with a note that implementation is pending
        return {
            'success': True,
            'output': f'[SSH Execution Placeholder] Command: {formatted_command}\n[Note: Actual SSH implementation pending]',
            'error': None,
            'exit_code': 0,
            'protocol': 'ssh',
            'device_ip': management_ip
        }
    
    async def _execute_telnet(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]],
        timeout: int,
        vendor: str
    ) -> Dict[str, Any]:
        """Execute command via Telnet"""
        # TODO: Implement Telnet connection
        management_ip = device.get('management_ip')
        port = device.get('management_port', 23)
        
        logger.info(f"Executing Telnet command on {management_ip}:{port}")
        
        return {
            'success': False,
            'error': 'Telnet execution not yet implemented',
            'output': '',
            'exit_code': 1
        }
    
    async def _execute_api(
        self,
        device: Dict[str, Any],
        command: str,
        credential: Optional[Dict[str, Any]],
        timeout: int,
        vendor: str
    ) -> Dict[str, Any]:
        """Execute command via REST API (for devices with API support)"""
        # TODO: Implement vendor-specific API calls (Cisco DNA Center, Juniper REST, etc.)
        management_ip = device.get('management_ip')
        api_key = credential.get('api_key') if credential else None
        
        logger.info(f"Executing API command on {management_ip} (vendor={vendor})")
        
        return {
            'success': False,
            'error': 'API execution not yet implemented',
            'output': '',
            'exit_code': 1
        }
    
    def _format_command_for_vendor(self, command: str, vendor: str, device: Dict[str, Any]) -> str:
        """Format command based on vendor/OS type"""
        vendor_lower = vendor.lower()
        model = (device.get('model') or '').lower()
        
        # Cisco IOS/NX-OS commands
        if 'cisco' in vendor_lower or 'ios' in model or 'nx' in model:
            # Ensure commands are in enable mode if needed
            if command.startswith('show') or command.startswith('display'):
                return command
            elif command.startswith('configure') or command.startswith('config'):
                return f'enable\n{command}'
            else:
                return command
        
        # Juniper JunOS commands
        elif 'juniper' in vendor_lower or 'junos' in model:
            # JunOS uses 'show' and 'set' commands
            if command.startswith('show'):
                return command
            elif command.startswith('set') or command.startswith('delete'):
                return f'configure\n{command}\ncommit'
            else:
                return command
        
        # Default: return as-is
        return command
    
    async def backup_config(
        self,
        device: Dict[str, Any],
        credential: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Backup device configuration before making changes
        
        Returns:
            Configuration text or None if backup fails
        """
        try:
            vendor = (device.get('vendor') or '').lower()
            model = (device.get('model') or '').lower()
            
            # Determine backup command based on vendor
            if 'cisco' in vendor or 'ios' in model or 'nx' in model:
                backup_command = 'show running-config'
            elif 'juniper' in vendor or 'junos' in model:
                backup_command = 'show configuration'
            elif 'palo' in vendor or 'fortinet' in vendor:
                backup_command = 'show running-config'  # May vary
            else:
                backup_command = 'show running-config'  # Default
            
            result = await self.execute_command(device, backup_command, credential)
            
            if result['success']:
                config = result['output']
                logger.info(f"Backed up config for device {device.get('name')} ({len(config)} chars)")
                return config
            else:
                logger.warning(f"Failed to backup config: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error backing up device config: {e}", exc_info=True)
            return None
    
    async def rollback_config(
        self,
        device: Dict[str, Any],
        backup_config: str,
        credential: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Rollback device to previous configuration
        
        Args:
            device: Network device info
            backup_config: Previously backed up configuration
            credential: Device credentials
        
        Returns:
            Dict with 'success', 'output', 'error'
        """
        try:
            vendor = (device.get('vendor') or '').lower()
            model = (device.get('model') or '').lower()
            
            # Vendor-specific rollback commands
            if 'cisco' in vendor or 'ios' in model or 'nx' in model:
                # For Cisco, we'd typically use 'configure replace' or restore from file
                # For now, return a placeholder
                rollback_command = 'configure replace flash:backup-config'
            elif 'juniper' in vendor or 'junos' in model:
                # Juniper: rollback 0 (previous config) or load override
                rollback_command = 'rollback 0'
            else:
                rollback_command = 'rollback'  # Generic
            
            result = await self.execute_command(device, rollback_command, credential)
            
            if result['success']:
                logger.info(f"Rolled back config for device {device.get('name')}")
            else:
                logger.error(f"Rollback failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error rolling back device config: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'output': ''
            }
    
    async def test_connection(
        self,
        device: Dict[str, Any],
        credential: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Test connectivity to network device
        
        Returns:
            Dict with 'success', 'message', 'latency_ms'
        """
        try:
            management_ip = device.get('management_ip')
            port = device.get('management_port', 22)
            protocol = device.get('connection_protocol', 'ssh').lower()
            
            if protocol == 'ssh':
                # Test SSH connectivity (simplified - just ping for now)
                import subprocess
                import platform
                
                # Ping test
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                result = subprocess.run(
                    ['ping', param, '1', management_ip],
                    capture_output=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'message': f'Device {management_ip} is reachable',
                        'latency_ms': None,
                        'protocol': protocol
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Device {management_ip} is not reachable',
                        'latency_ms': None,
                        'protocol': protocol
                    }
            else:
                return {
                    'success': False,
                    'message': f'Connection testing for {protocol} not yet implemented',
                    'latency_ms': None
                }
                
        except Exception as e:
            logger.error(f"Error testing device connection: {e}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'latency_ms': None
            }


