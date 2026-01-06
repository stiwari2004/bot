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
        """Execute command via SSH using asyncssh (preferred) or paramiko (fallback)"""
        management_ip = device.get('management_ip')
        if not management_ip:
            return {
                'success': False,
                'error': 'Management IP address is required',
                'output': '',
                'exit_code': 1
            }
        
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
        
        # Try asyncssh first (async-native, better for async code)
        try:
            import asyncssh
            return await self._execute_ssh_asyncssh(
                management_ip, port, username, password, formatted_command, timeout, vendor
            )
        except ImportError:
            logger.debug("asyncssh not available, trying paramiko")
            # Fallback to paramiko
            try:
                return await self._execute_ssh_paramiko(
                    management_ip, port, username, password, formatted_command, timeout, vendor
                )
            except ImportError:
                return {
                    'success': False,
                    'error': 'Neither asyncssh nor paramiko is installed. Install one: pip install asyncssh or pip install paramiko',
                    'output': '',
                    'exit_code': 1
                }
        except Exception as e:
            logger.error(f"SSH execution failed with asyncssh: {e}", exc_info=True)
            # Try paramiko as fallback
            try:
                return await self._execute_ssh_paramiko(
                    management_ip, port, username, password, formatted_command, timeout, vendor
                )
            except Exception as e2:
                logger.error(f"SSH execution failed with paramiko: {e2}", exc_info=True)
                return {
                    'success': False,
                    'error': f'SSH execution failed: {str(e)}',
                    'output': '',
                    'exit_code': 1
                }
    
    async def _execute_ssh_asyncssh(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        command: str,
        timeout: int,
        vendor: str
    ) -> Dict[str, Any]:
        """Execute SSH command using asyncssh library"""
        import asyncssh
        
        try:
            # Connect to SSH server
            async with asyncssh.connect(
                host,
                port=port,
                username=username,
                password=password,
                known_hosts=None,  # Accept any host key (for automation)
                connect_timeout=timeout,
                login_timeout=timeout
            ) as conn:
                # Execute command
                result = await conn.run(command, timeout=timeout)
                
                return {
                    'success': result.exit_status == 0,
                    'output': result.stdout,
                    'error': result.stderr if result.exit_status != 0 else None,
                    'exit_code': result.exit_status,
                    'protocol': 'ssh',
                    'device_ip': host
                }
        except asyncssh.Error as e:
            logger.error(f"asyncssh connection error: {e}")
            return {
                'success': False,
                'error': f'SSH connection failed: {str(e)}',
                'output': '',
                'exit_code': 1,
                'protocol': 'ssh',
                'device_ip': host
            }
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f'SSH command timed out after {timeout} seconds',
                'output': '',
                'exit_code': 1,
                'protocol': 'ssh',
                'device_ip': host
            }
    
    async def _execute_ssh_paramiko(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        command: str,
        timeout: int,
        vendor: str
    ) -> Dict[str, Any]:
        """Execute SSH command using paramiko library (fallback)"""
        import paramiko
        from paramiko.ssh_exception import (
            SSHException, AuthenticationException, BadHostKeyException
        )
        
        try:
            # Run paramiko in executor since it's synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_paramiko_command,
                host, port, username, password, command, timeout
            )
            return result
        except Exception as e:
            logger.error(f"paramiko execution error: {e}")
            return {
                'success': False,
                'error': f'SSH execution failed: {str(e)}',
                'output': '',
                'exit_code': 1,
                'protocol': 'ssh',
                'device_ip': host
            }
    
    def _run_paramiko_command(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        command: str,
        timeout: int
    ) -> Dict[str, Any]:
        """Synchronous paramiko command execution (runs in executor)"""
        import paramiko
        from paramiko.ssh_exception import (
            SSHException, AuthenticationException, BadHostKeyException
        )
        
        client = None
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to SSH server
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )
            
            # Execute command
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            
            # Read output
            output = stdout.read().decode('utf-8', errors='replace')
            error_output = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                'success': exit_code == 0,
                'output': output,
                'error': error_output if exit_code != 0 else None,
                'exit_code': exit_code,
                'protocol': 'ssh',
                'device_ip': host
            }
        except AuthenticationException as e:
            return {
                'success': False,
                'error': f'SSH authentication failed: {str(e)}',
                'output': '',
                'exit_code': 1,
                'protocol': 'ssh',
                'device_ip': host
            }
        except SSHException as e:
            return {
                'success': False,
                'error': f'SSH connection error: {str(e)}',
                'output': '',
                'exit_code': 1,
                'protocol': 'ssh',
                'device_ip': host
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'SSH execution failed: {str(e)}',
                'output': '',
                'exit_code': 1,
                'protocol': 'ssh',
                'device_ip': host
            }
        finally:
            if client:
                client.close()
    
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









