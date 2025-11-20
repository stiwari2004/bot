"""
YAML generator for different service types
"""
import yaml
from datetime import datetime
from typing import Dict, Any, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)


class YamlGenerator:
    """Generates YAML runbooks for different service types"""
    
    def generate_yaml(self, service: str, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Generate YAML based on service type"""
        if service == "server":
            return self.generate_server_yaml(issue, env, risk)
        elif service == "database":
            return self.generate_database_yaml(issue, env, risk)
        elif service == "web":
            return self.generate_web_application_yaml(issue, env, risk)
        elif service == "storage":
            return self.generate_storage_yaml(issue, env, risk)
        elif service == "network":
            return self.generate_network_connectivity_yaml(issue, env, risk)
        else:
            # Default to server
            return self.generate_server_yaml(issue, env, risk)
    
    def generate_server_yaml(self, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Generate server performance troubleshooting runbook."""
        spec: Dict[str, Any] = {
            "runbook_id": "rb-server-performance",
            "version": "1.0.0",
            "title": "Resolve Server Performance Issues",
            "service": "server",
            "env": env,
            "risk": risk,
            "owner": "IT-Server-Team",
            "last_tested": datetime.now().strftime("%Y-%m-%d"),
            "review_required": True,
            "description": (
                "This runbook provides structured steps for diagnosing and resolving "
                "server performance issues including high CPU usage, memory problems, "
                "local disk space issues, and general server slowdowns. Intended for "
                "automated or semi-automated execution."
            ),
            "inputs": [
                {
                    "name": "server_host",
                    "type": "string",
                    "required": True,
                    "description": "Server hostname or IP address"
                },
                {
                    "name": "disk_path",
                    "type": "string",
                    "required": False,
                    "default": "/",
                    "description": "Local disk path to check (default: root filesystem)"
                }
            ],
            "prechecks": [
                {
                    "description": "Verify server is reachable",
                    "command": "ping -c 3 {{server_host}}",
                    "expected_output": "0% packet loss"
                },
                {
                    "description": "Check server uptime",
                    "command": "ssh {{server_host}} 'uptime'",
                    "expected_output": "load average"
                }
            ],
            "steps": [
                {
                    "name": "Step 1 - Check CPU Usage",
                    "type": "command",
                    "command": "ssh {{server_host}} 'top -bn1 | grep Cpu'",
                    "parse_output": True,
                    "notes": "Identify CPU utilization percentage"
                },
                {
                    "name": "Step 2 - Check Memory Usage",
                    "type": "command",
                    "command": "ssh {{server_host}} 'free -h'",
                    "parse_output": True,
                    "notes": "Check memory consumption and swap usage"
                },
                {
                    "name": "Step 3 - Check Disk Space",
                    "type": "command",
                    "command": "ssh {{server_host}} 'df -h {{disk_path}}'",
                    "parse_output": True,
                    "notes": "Verify local disk space availability"
                },
                {
                    "name": "Step 4 - Identify Top Resource Consumers",
                    "type": "command",
                    "command": "ssh {{server_host}} 'ps aux --sort=-%cpu | head -10'",
                    "parse_output": True,
                    "notes": "List processes consuming the most CPU"
                },
                {
                    "name": "Step 5 - Check System Load",
                    "type": "command",
                    "command": "ssh {{server_host}} 'uptime'",
                    "parse_output": True,
                    "notes": "Review system load average"
                },
                {
                    "name": "Step 6 - Restart Service if Needed",
                    "type": "command",
                    "precondition": "cpu_usage > 90 OR memory_usage > 90",
                    "command": "ssh {{server_host}} 'systemctl restart <service_name>'",
                    "rollback": "ssh {{server_host}} 'systemctl start <service_name>'",
                    "timeout": 60,
                    "notes": "Replace <service_name> with actual service name"
                }
            ],
            "postchecks": [
                {
                    "description": "Verify server is responding",
                    "command": "ping -c 3 {{server_host}}",
                    "expected_output": "0% packet loss"
                },
                {
                    "description": "Check CPU usage is normalized",
                    "command": "ssh {{server_host}} 'top -bn1 | grep Cpu | awk \"{print \\$2}\"'",
                    "expected_output": "< 80"
                },
                {
                    "description": "Verify disk space is available",
                    "command": "ssh {{server_host}} 'df -h {{disk_path}} | awk \"NR==2 {print \\$5}\" | sed \"s/%//\"'",
                    "expected_output": "< 85"
                }
            ],
            "recommendations": [
                "Implement server monitoring (CPU, memory, disk)",
                "Set up automated alerts for resource thresholds",
                "Regular server maintenance and updates",
                "Review and optimize application code if resource usage is excessive",
                "Consider scaling up resources if consistently high"
            ],
            "references": [
                {
                    "name": "Linux Performance Monitoring Guide",
                    "url": "https://www.kernel.org/doc/Documentation/sysctl/vm.txt"
                },
                {
                    "name": "Server Troubleshooting Best Practices",
                    "url": "https://kb.company.local/server/troubleshooting"
                }
            ],
            "audit": {
                "log_level": "verbose",
                "capture_outputs": True,
                "record_duration": True,
                "notify_on_completion": ["server-team@company.com"]
            },
            "disclaimer": (
                "This runbook is AI-generated and human-reviewed. Use only in approved environments "
                "with guardrails enabled. Validate commands in non-production before enabling auto-execution."
            )
        }

        yaml_str = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
        return yaml_str, spec

    def generate_database_yaml(self, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Generate database troubleshooting runbook."""
        spec: Dict[str, Any] = {
            "runbook_id": "rb-database-performance",
            "version": "1.0.0",
            "title": "Resolve Database Performance Issues",
            "service": "database",
            "env": env,
            "risk": risk,
            "owner": "IT-Database-Team",
            "last_tested": datetime.now().strftime("%Y-%m-%d"),
            "review_required": True,
            "description": (
                "This runbook provides structured steps for diagnosing and resolving "
                "database performance issues including slow queries, connection problems, "
                "and resource constraints. Intended for automated or semi-automated execution."
            ),
            "inputs": [
                {
                    "name": "db_host",
                    "type": "string",
                    "required": True,
                    "description": "Database host or connection string"
                },
                {
                    "name": "db_name",
                    "type": "string",
                    "required": True,
                    "description": "Database name to troubleshoot"
                },
                {
                    "name": "db_user",
                    "type": "string",
                    "required": False,
                    "default": "monitoring",
                    "description": "Database user for diagnostics"
                }
            ],
            "prechecks": [
                {
                    "description": "Verify database service is running",
                    "command": "systemctl status postgresql",
                    "expected_output": "active (running)"
                },
                {
                    "description": "Check database connectivity",
                    "command": "psql -h {{db_host}} -U {{db_user}} -d {{db_name}} -c 'SELECT 1'",
                    "expected_output": "1"
                }
            ],
            "steps": [
                {
                    "name": "Step 1 - Check Database Status",
                    "type": "command",
                    "command": "psql -h {{db_host}} -U {{db_user}} -d {{db_name}} -c 'SELECT version()'",
                    "timeout": 30
                },
                {
                    "name": "Step 2 - Analyze Slow Queries",
                    "type": "command",
                    "command": "psql -h {{db_host}} -U {{db_user}} -d {{db_name}} -c \"SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10\"",
                    "parse_output": True,
                    "notes": "Identify queries consuming the most time"
                },
                {
                    "name": "Step 3 - Check Connection Count",
                    "type": "command",
                    "command": "psql -h {{db_host}} -U {{db_user}} -d {{db_name}} -c \"SELECT count(*) as connections FROM pg_stat_activity\"",
                    "expected_output": "connections"
                },
                {
                    "name": "Step 4 - Check Disk Usage",
                    "type": "command",
                    "command": "df -h /var/lib/postgresql",
                    "parse_output": True
                },
                {
                    "name": "Step 5 - Restart Database Service",
                    "type": "command",
                    "precondition": "previous_step.failed == true",
                    "command": "systemctl restart postgresql",
                    "rollback": "systemctl start postgresql",
                    "timeout": 60
                }
            ],
            "postchecks": [
                {
                    "description": "Verify database is responding",
                    "command": "psql -h {{db_host}} -U {{db_user}} -d {{db_name}} -c 'SELECT 1'",
                    "expected_output": "1"
                }
            ],
            "recommendations": [
                "Implement query performance monitoring",
                "Set up connection pooling",
                "Regular database maintenance and vacuuming",
                "Monitor disk space and growth trends"
            ],
            "references": [
                {
                    "name": "PostgreSQL Performance Tuning Guide",
                    "url": "https://www.postgresql.org/docs/current/performance-tips.html"
                }
            ],
            "audit": {
                "log_level": "verbose",
                "capture_outputs": True,
                "record_duration": True,
                "notify_on_completion": ["dba-team@company.com"]
            },
            "disclaimer": (
                "This runbook is AI-generated and human-reviewed. Use only in approved environments "
                "with guardrails enabled. Validate commands in non-production before enabling auto-execution."
            )
        }

        yaml_str = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
        return yaml_str, spec

    def generate_web_application_yaml(self, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Generate web application troubleshooting runbook."""
        spec: Dict[str, Any] = {
            "runbook_id": "rb-web-application-performance",
            "version": "1.0.0",
            "title": "Resolve Web Application Performance Issues",
            "service": "web",
            "env": env,
            "risk": risk,
            "owner": "IT-Web-Team",
            "last_tested": datetime.now().strftime("%Y-%m-%d"),
            "review_required": True,
            "description": (
                "This runbook provides structured steps for diagnosing and resolving "
                "web application performance issues including slow responses, high CPU usage, "
                "and memory problems. Intended for automated or semi-automated execution."
            ),
            "inputs": [
                {
                    "name": "app_url",
                    "type": "string",
                    "required": True,
                    "description": "Web application URL to test"
                },
                {
                    "name": "app_port",
                    "type": "string",
                    "required": False,
                    "default": "80",
                    "description": "Application port number"
                }
            ],
            "prechecks": [
                {
                    "description": "Verify web server is running",
                    "command": "systemctl status nginx",
                    "expected_output": "active (running)"
                },
                {
                    "description": "Check application port",
                    "command": "netstat -tlnp | grep :{{app_port}}",
                    "expected_output": "LISTEN"
                }
            ],
            "steps": [
                {
                    "name": "Step 1 - Check Application Health",
                    "type": "command",
                    "command": "curl -I {{app_url}}",
                    "expected_output": "HTTP/1.1 200",
                    "timeout": 30
                },
                {
                    "name": "Step 2 - Check CPU Usage",
                    "type": "command",
                    "command": "top -bn1 | grep 'Cpu(s)'",
                    "parse_output": True
                },
                {
                    "name": "Step 3 - Check Memory Usage",
                    "type": "command",
                    "command": "free -m",
                    "parse_output": True
                },
                {
                    "name": "Step 4 - Restart Application",
                    "type": "command",
                    "precondition": "previous_step.failed == true",
                    "command": "systemctl restart nginx",
                    "rollback": "systemctl start nginx",
                    "timeout": 30
                }
            ],
            "postchecks": [
                {
                    "description": "Verify application is responding",
                    "command": "curl -I {{app_url}}",
                    "expected_output": "HTTP/1.1 200"
                }
            ],
            "recommendations": [
                "Implement application performance monitoring",
                "Set up load balancing",
                "Regular application updates and patches",
                "Monitor resource usage trends"
            ],
            "references": [
                {
                    "name": "Nginx Performance Tuning",
                    "url": "https://nginx.org/en/docs/http/ngx_http_core_module.html"
                }
            ],
            "audit": {
                "log_level": "verbose",
                "capture_outputs": True,
                "record_duration": True,
                "notify_on_completion": ["web-team@company.com"]
            },
            "disclaimer": (
                "This runbook is AI-generated and human-reviewed. Use only in approved environments "
                "with guardrails enabled. Validate commands in non-production before enabling auto-execution."
            )
        }

        yaml_str = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
        return yaml_str, spec

    def generate_storage_yaml(self, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Generate storage troubleshooting runbook."""
        spec: Dict[str, Any] = {
            "runbook_id": "rb-storage-issues",
            "version": "1.0.0",
            "title": "Resolve Storage Issues",
            "service": "storage",
            "env": env,
            "risk": risk,
            "owner": "IT-Storage-Team",
            "last_tested": datetime.now().strftime("%Y-%m-%d"),
            "review_required": True,
            "description": (
                "This runbook provides structured steps for diagnosing and resolving "
                "storage issues including disk space, filesystem problems, and mount issues "
                "for external storage systems (NAS, SAN, network storage). Intended for "
                "automated or semi-automated execution."
            ),
            "inputs": [
                {
                    "name": "mount_point",
                    "type": "string",
                    "required": True,
                    "description": "Filesystem mount point to check"
                },
                {
                    "name": "threshold_percent",
                    "type": "string",
                    "required": False,
                    "default": "80",
                    "description": "Disk usage threshold percentage"
                }
            ],
            "prechecks": [
                {
                    "description": "Check if mount point exists",
                    "command": "test -d {{mount_point}}",
                    "expected_output": "0"
                },
                {
                    "description": "Verify filesystem is mounted",
                    "command": "mount | grep {{mount_point}}",
                    "expected_output": "on {{mount_point}}"
                }
            ],
            "steps": [
                {
                    "name": "Step 1 - Check Disk Usage",
                    "type": "command",
                    "command": "df -h {{mount_point}}",
                    "parse_output": True
                },
                {
                    "name": "Step 2 - Find Large Files",
                    "type": "command",
                    "command": "find {{mount_point}} -type f -size +100M -exec ls -lh {} \\;",
                    "parse_output": True,
                    "notes": "Identify files consuming the most space"
                },
                {
                    "name": "Step 3 - Clean Temporary Files",
                    "type": "command",
                    "precondition": "disk_usage > threshold_percent",
                    "command": "find {{mount_point}} -name '*.tmp' -mtime +7 -delete",
                    "timeout": 300
                },
                {
                    "name": "Step 4 - Check Filesystem Health",
                    "type": "command",
                    "command": "fsck -n {{mount_point}}",
                    "timeout": 60
                }
            ],
            "postchecks": [
                {
                    "description": "Verify disk usage is below threshold",
                    "command": "df -h {{mount_point}} | awk 'NR==2 {print $5}' | sed 's/%//'",
                    "expected_output": "< {{threshold_percent}}"
                }
            ],
            "recommendations": [
                "Implement disk usage monitoring",
                "Set up automated cleanup jobs",
                "Regular filesystem maintenance",
                "Monitor storage growth trends"
            ],
            "references": [
                {
                    "name": "Linux Filesystem Management",
                    "url": "https://www.kernel.org/doc/Documentation/filesystems/"
                }
            ],
            "audit": {
                "log_level": "verbose",
                "capture_outputs": True,
                "record_duration": True,
                "notify_on_completion": ["storage-team@company.com"]
            },
            "disclaimer": (
                "This runbook is AI-generated and human-reviewed. Use only in approved environments "
                "with guardrails enabled. Validate commands in non-production before enabling auto-execution."
            )
        }

        yaml_str = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
        return yaml_str, spec

    def generate_network_connectivity_yaml(self, issue: str, env: str, risk: str) -> Tuple[str, Dict[str, Any]]:
        """Produce an atomic, agent-executable runbook for office connectivity."""
        spec: Dict[str, Any] = {
            "runbook_id": "rb-network-connectivity-office",
            "version": "1.0.0",
            "title": "Resolve Office Network Connectivity Issues",
            "service": "network",
            "env": env,
            "risk": risk,
            "owner": "IT-Network-Team",
            "last_tested": datetime.now().strftime("%Y-%m-%d"),
            "review_required": True,
            "description": (
                "This runbook provides structured steps for diagnosing and resolving "
                "office network connectivity issues caused by physical, configuration, "
                "or routing problems. Intended for automated or semi-automated execution "
                "by the Virtual Infrastructure Agent."
            ),
            "inputs": [
                {
                    "name": "host_ip",
                    "type": "string",
                    "required": True,
                    "description": "Target host or service IP to test connectivity"
                },
                {
                    "name": "gateway_ip",
                    "type": "string",
                    "required": True,
                    "description": "Gateway or router IP to verify network reachability"
                },
                {
                    "name": "interface",
                    "type": "string",
                    "required": False,
                    "default": "eth0",
                    "description": "Network interface to restart during remediation"
                }
            ],
            "prechecks": [
                {
                    "description": "Verify local host has IP assigned to the target interface",
                    "command": "ip addr show {{interface}} | grep 'inet '",
                    "expected_output": "inet "
                },
                {
                    "description": "Ensure DNS resolution is functioning",
                    "command": "nslookup google.com",
                    "expected_output": "Address"
                }
            ],
            "steps": [
                {
                    "name": "Step 1 - Check Physical Connections",
                    "type": "manual",
                    "description": (
                        "Ensure all network cables, switches, and access points are connected and powered. "
                        "If possible, verify link lights on the switch port and NIC."
                    ),
                    "skip_in_auto_mode": True
                },
                {
                    "name": "Step 2 - Verify Gateway Connectivity",
                    "type": "command",
                    "command": "ping -c 4 {{gateway_ip}}",
                    "expected_output": "0% packet loss",
                    "timeout": 30,
                    "on_fail": "run Step 3 - Restart Network Interface"
                },
                {
                    "name": "Step 3 - Restart Network Interface",
                    "type": "command",
                    "precondition": "previous_step.failed == true",
                    "command": "nmcli connection up {{interface}}",
                    "rollback": "nmcli connection down {{interface}}",
                    "verify_command": "ping -c 4 {{gateway_ip}}",
                    "expected_output": "0% packet loss"
                },
                {
                    "name": "Step 4 - Trace Route to Host",
                    "type": "command",
                    "command": "traceroute {{host_ip}}",
                    "parse_output": True,
                    "notes": (
                        "Use traceroute output to detect routing loops or unreachable hops. "
                        "Useful for escalation to network ops."
                    )
                },
                {
                    "name": "Step 5 - Verify End-to-End Connectivity",
                    "type": "verify",
                    "command": "ping -c 4 {{host_ip}}",
                    "expected_output": "0% packet loss"
                },
                {
                    "name": "Step 6 - Validate Internal Access",
                    "type": "verify",
                    "command": "curl -Is https://intranet.company.local",
                    "expected_output": "HTTP/1.1 200 OK"
                }
            ],
            "postchecks": [
                {
                    "description": "Confirm all services dependent on the network are operational",
                    "command": "systemctl list-units --type=service | grep network",
                    "expected_output": "active (running)"
                },
                {
                    "description": "Review syslogs for recurring network failures",
                    "command": "grep -i 'link down' /var/log/syslog | tail -n 10",
                    "optional": True
                }
            ],
            "recommendations": [
                "Implement ICMP and gateway monitoring via Prometheus or Zabbix",
                "Document switch port mapping for all key endpoints",
                "Review and patch network drivers monthly",
                "Maintain offline config backup of all switches"
            ],
            "references": [
                {
                    "name": "Internal Network Troubleshooting Guide",
                    "url": "https://kb.company.local/network/troubleshooting"
                },
                {
                    "name": "Vendor Switch Diagnostics Manual",
                    "url": "https://support.vendor.com/switches/diagnostics"
                }
            ],
            "audit": {
                "log_level": "verbose",
                "capture_outputs": True,
                "record_duration": True,
                "notify_on_completion": ["network-team@company.com"]
            },
            "disclaimer": (
                "This runbook is AI-generated and human-reviewed. Use only in approved environments "
                "with guardrails enabled. Validate commands in non-production before enabling auto-execution."
            )
        }

        yaml_str = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
        return yaml_str, spec


