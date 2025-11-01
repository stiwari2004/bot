"""
Runbook generation service using RAG pipeline
"""
import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.schemas.search import SearchResult
from app.schemas.runbook import RunbookCreate, RunbookResponse
from app.models.runbook import Runbook
from app.services.vector_store import VectorStoreService
from app.services.llm_service import get_llm_service
from app.core.logging import get_logger
import yaml

logger = get_logger(__name__)


class RunbookGeneratorService:
    """Service for generating runbooks from search results using RAG"""
    
    def __init__(self):
        self.vector_service = VectorStoreService()
    
    async def generate_runbook(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        top_k: int = 5,
        source_types: Optional[List[str]] = None
    ) -> RunbookResponse:
        """Generate a runbook from issue description using RAG"""
        
        # Step 1: Search for relevant knowledge (using hybrid search)
        search_results = await self.vector_service.hybrid_search(
            query=issue_description,
            tenant_id=tenant_id,
            db=db,
            top_k=top_k,
            source_types=source_types,
            use_reranking=True
        )
        
        # Step 2: Generate runbook content using retrieved knowledge
        runbook_content = await self._generate_content(issue_description, search_results)
        
        # Step 3: Calculate confidence score
        confidence = self._calculate_confidence(search_results)
        
        # Step 4: Create runbook record
        runbook = Runbook(
            tenant_id=tenant_id,
            title=f"Runbook: {issue_description[:100]}...",
            body_md=runbook_content,
            meta_data=json.dumps({
                "issue_description": issue_description,
                "sources_used": len(search_results),
                "search_query": issue_description,
                "generated_by": "rag_pipeline"
            }),
            confidence=confidence,
            is_active="active"
        )
        
        db.add(runbook)
        db.commit()
        db.refresh(runbook)
        
        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=runbook.confidence,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            created_at=runbook.created_at,
            updated_at=runbook.updated_at
        )

    async def generate_agent_runbook(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        service: str = "auto",
        env: str = "prod",
        risk: str = "low",
        top_k: int = 5
    ) -> RunbookResponse:
        """Generate an agent-executable, atomic YAML runbook.
        Auto-detects service type from issue description if service="auto".
        """
        # Auto-detect service type if not specified
        if service == "auto":
            service = await self._detect_service_type(issue_description)

        # RAG: retrieve top context to condition the LLM (using hybrid search)
        search_results = await self.vector_service.hybrid_search(
            query=issue_description,
            tenant_id=tenant_id,
            db=db,
            top_k=top_k,
            source_types=None,
            use_reranking=True
        )
        context = self._build_context(search_results) if search_results else ""

        # Ask LLM to produce YAML runbook per schema
        llm = get_llm_service()
        try:
            logger.debug(f"LLM provider: {type(llm).__name__} base={getattr(llm, 'base_url', None)} model_id={getattr(llm, 'model_id', None)}")
        except Exception:
            pass
        ai_yaml = await llm.generate_yaml_runbook(
            issue_description=issue_description,
            service_type=service,
            env=env,
            risk=risk,
            context=context,
        )
        
        logger.debug(f"LLM returned YAML length={len(ai_yaml) if ai_yaml else 0}, first 500 chars: {ai_yaml[:500] if ai_yaml else 'None'}")

        # Strip code fences if present
        if ai_yaml and ai_yaml.strip().startswith("```"):
            lines = ai_yaml.strip().split("\n")
            # Remove first ```yaml or ``` line
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove trailing ``` if present
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            ai_yaml = "\n".join(lines)
            logger.debug(f"After stripping fences: length={len(ai_yaml)}, first 200: {ai_yaml[:200]}")
        
        # Sanitize LLM output: remove problematic patterns from description fields
        ai_yaml = self._sanitize_description_field(ai_yaml)

        # Validate YAML. If invalid, DO NOT fallback - return error to surface LLM wiring issues
        try:
            if not ai_yaml or not ai_yaml.strip():
                raise ValueError("empty ai yaml")
            spec = yaml.safe_load(ai_yaml)
            if not isinstance(spec, dict):
                logger.error(f"YAML did not parse to dict: type={type(spec)}, value={str(spec)[:200]}")
                raise ValueError("invalid spec shape - not a dict")
            if "steps" not in spec:
                logger.error(f"YAML dict missing 'steps' key: keys={list(spec.keys())}")
                raise ValueError("invalid spec shape - missing steps")
            
            # Post-process: fix common LLM YAML formatting issues
            if "inputs" in spec and isinstance(spec["inputs"], dict):
                # Convert dict inputs to list format
                fixed_inputs = []
                for name, value in spec["inputs"].items():
                    fixed_inputs.append({
                        "name": name,
                        "type": "string",
                        "required": True,
                        "description": f"Parameter: {name}"
                    })
                spec["inputs"] = fixed_inputs
                logger.debug(f"Fixed inputs: converted dict to list format with {len(fixed_inputs)} items")
            
            # Fix postchecks if it's a single dict instead of a list
            if "postchecks" in spec and isinstance(spec["postchecks"], dict):
                spec["postchecks"] = [spec["postchecks"]]
                logger.debug("Fixed postchecks: converted single dict to list format")
            
            # Ensure required fields with defaults
            if "env" not in spec:
                spec["env"] = env
            if "risk" not in spec:
                spec["risk"] = risk
            
            # Validate runbook structure and command safety
            try:
                from app.schemas.runbook_yaml import RunbookValidator
                validated_spec, warnings = RunbookValidator.validate_runbook(spec, auto_assign_severity=True)
                if warnings:
                    logger.warning(f"Runbook validation warnings: {warnings}")
                # Use validated spec (converts to model and back, but ensures valid structure)
                spec = validated_spec.model_dump(mode='json', exclude_none=True)
                logger.info(f"Runbook validated: {len(spec.get('steps', []))} steps, all commands checked")
            except Exception as e:
                logger.warning(f"Runbook validation failed but continuing: {type(e).__name__}: {e}")
                # Continue but note the validation issue
            
            runbook_yaml = yaml.safe_dump(spec, sort_keys=False, default_flow_style=False, width=120)
            generation_mode = "ai"
        except Exception as e:
            logger.error(f"AI YAML invalid or empty – rejecting request (no fallback): {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail=f"LLM YAML generation failed: {type(e).__name__}: {str(e)[:200]}")

        # Persist as Markdown (code fence) for readability while storing JSON spec in meta_data
        body_md = f"""# Agent Runbook (YAML)

```yaml
{runbook_yaml}
```
"""

        runbook = Runbook(
            tenant_id=tenant_id,
            title=f"Runbook: {spec.get('title')}",
            body_md=body_md,
            meta_data=json.dumps({
                "issue_description": issue_description,
                "generated_by": "agent_yaml",
                "service": service,
                "env": env,
                "risk": risk,
                "runbook_spec": spec,
                "generation_mode": generation_mode
            }),
            confidence=0.75,
            is_active="active"
        )

        db.add(runbook)
        db.commit()
        db.refresh(runbook)

        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=runbook.confidence,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            created_at=runbook.created_at,
            updated_at=runbook.updated_at
        )

    def _generate_network_connectivity_yaml(self, issue: str, env: str, risk: str) -> tuple[str, Dict[str, Any]]:
        """Produce an atomic, agent-executable runbook for office connectivity."""
        from datetime import datetime
        
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

    async def _detect_service_type(self, issue_description: str) -> str:
        """Detect service type using keyword matching only (LLM disabled due to inaccuracy)."""
        keyword_guess = self._keyword_classify_service_type(issue_description)
        logger.debug(f"Service detection: returning keyword={keyword_guess} (LLM classification disabled)")
        return keyword_guess
    
    def _keyword_classify_service_type(self, issue_description: str) -> str:
        """Detect service type from issue description using enhanced keyword matching."""
        issue_lower = issue_description.lower()
        
        # Score each service type based on keyword matches
        scores = {
            'server': 0,
            'storage': 0,
            'database': 0,
            'web': 0,
            'network': 0
        }
        
        # Server keywords with weights (CPU, memory, general performance, local disk)
        server_patterns = {
            'server is': 3, 'server running': 3, 'server slow': 3, 'server performance': 3,
            'cpu usage': 3, 'high cpu': 3, 'cpu high': 3, 'cpu load': 3,
            'memory usage': 3, 'high memory': 3, 'memory high': 3, 'out of memory': 3,
            'server disk': 2, 'local disk': 2, 'server storage': 2,
            'performance issue': 2, 'slow server': 3, 'server timeout': 2,
            'resource': 1, 'server': 1, 'host': 1
        }
        
        # Storage keywords with weights (external storage systems)
        storage_patterns = {
            'nas': 3, 'san': 3, 'network storage': 3, 'network attached': 3,
            'storage array': 3, 'storage system': 3, 'shared storage': 3,
            'external storage': 3, 'storage network': 3,
            'nfs mount': 2, 'cifs mount': 2, 'network share': 2,
            'storage volume': 2, 'storage capacity': 2,
            'storage': 1  # Lower weight, can be ambiguous
        }
        
        # Database keywords with weights (specific DB issues)
        db_patterns = {
            'database': 3, 'db': 2, 'mysql': 3, 'postgres': 3, 'postgresql': 3,
            'oracle': 3, 'mongodb': 3, 'redis': 3, 'sql server': 3,
            'connection timeout': 2, 'query timeout': 2, 'slow query': 2,
            'connection pool': 2, 'deadlock': 2, 'transaction': 2,
            'sql': 1, 'query': 1
        }
        
        # Web application keywords with weights
        web_patterns = {
            'web server': 3, 'website': 3, 'web application': 3, 'web app': 3,
            'http error': 2, 'https error': 2, 'status code': 2, '404': 2, '500': 2,
            'api': 2, 'rest api': 2, 'endpoint': 2, 'response time': 2,
            'load balancer': 2, 'nginx': 2, 'apache': 2, 'iis': 2,
            'web': 1, 'http': 1, 'https': 1
        }
        
        # Network keywords with weights
        network_patterns = {
            'network connectivity': 3, 'network issue': 3, 'connection lost': 3,
            'ping': 2, 'traceroute': 2, 'dns': 2, 'dns resolution': 2,
            'firewall': 2, 'switch': 2, 'router': 2, 'cable': 2,
            'ip address': 2, 'subnet': 2, 'vlan': 2, 'routing': 2,
            'network': 1, 'connectivity': 1
        }
        
        # Calculate scores
        for pattern, weight in server_patterns.items():
            if pattern in issue_lower:
                scores['server'] += weight
                
        for pattern, weight in storage_patterns.items():
            if pattern in issue_lower:
                scores['storage'] += weight
                
        for pattern, weight in db_patterns.items():
            if pattern in issue_lower:
                scores['database'] += weight
                
        for pattern, weight in web_patterns.items():
            if pattern in issue_lower:
                scores['web'] += weight
                
        for pattern, weight in network_patterns.items():
            if pattern in issue_lower:
                scores['network'] += weight
        
        # Special handling: if "disk space" but no external storage indicators, it's server
        if 'disk space' in issue_lower or 'disk full' in issue_lower:
            if scores['storage'] < 2:  # No strong storage indicators
                scores['server'] += 3  # More likely server disk issue
                scores['storage'] = 0  # Suppress storage score
        
        # Return the service with highest score, default to server if tied
        max_score = max(scores.values())
        if max_score == 0:
            return "server"  # Default fallback (most common)
            
        for service, score in scores.items():
            if score == max_score:
                return service
                
        return "server"  # Final fallback

    def _generate_server_yaml(self, issue: str, env: str, risk: str) -> tuple[str, Dict[str, Any]]:
        """Generate server performance troubleshooting runbook."""
        from datetime import datetime
        
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

    def _generate_database_yaml(self, issue: str, env: str, risk: str) -> tuple[str, Dict[str, Any]]:
        """Generate database troubleshooting runbook."""
        from datetime import datetime
        
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

    def _generate_web_application_yaml(self, issue: str, env: str, risk: str) -> tuple[str, Dict[str, Any]]:
        """Generate web application troubleshooting runbook."""
        from datetime import datetime
        
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

    def _generate_storage_yaml(self, issue: str, env: str, risk: str) -> tuple[str, Dict[str, Any]]:
        """Generate storage troubleshooting runbook."""
        from datetime import datetime
        
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
    
    async def _generate_content(self, issue: str, search_results: List[SearchResult]) -> str:
        """Generate runbook content from search results"""
        
        if not search_results:
            return self._generate_fallback_content(issue)
        
        # Build context from search results
        context = self._build_context(search_results)
        
        # Generate structured runbook content
        runbook_content = f"""# Troubleshooting Runbook

## Issue Description
{issue}

## Root Cause Analysis
Based on similar incidents and knowledge base, this issue typically occurs due to:

{self._extract_root_causes(search_results)}

## Troubleshooting Steps

### Step 1: Initial Assessment
{self._generate_initial_assessment(search_results)}

### Step 2: Diagnostic Commands
```bash
{self._extract_diagnostic_commands(search_results)}
```

### Step 3: Resolution Steps
{self._generate_resolution_steps(search_results)}

### Step 4: Verification
{self._generate_verification_steps(search_results)}

## Prevention Measures
{self._generate_prevention_measures(search_results)}

## References
{self._generate_references(search_results)}

---
*This runbook was generated using AI and should be reviewed before implementation.*
"""
        
        return runbook_content
    
    def _build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results"""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"{i}. {result.text} (Source: {result.document_source}, Score: {result.score:.3f})")
        return "\n\n".join(context_parts)
    
    def _extract_root_causes(self, search_results: List[SearchResult]) -> str:
        """Extract potential root causes from search results"""
        causes = []
        for result in search_results[:3]:  # Top 3 results
            if "caused by" in result.text.lower() or "issue" in result.text.lower():
                # Extract the cause part
                text = result.text.lower()
                if "caused by" in text:
                    cause_part = text.split("caused by")[1].split(".")[0].strip()
                    causes.append(f"- {cause_part.capitalize()}")
                elif "common issues" in text:
                    cause_part = text.split("common issues")[1].split(".")[0].strip()
                    causes.append(f"- {cause_part.capitalize()}")
        
        if not causes:
            causes = ["- Configuration issues", "- Resource constraints", "- Network connectivity problems"]
        
        return "\n".join(causes[:3])
    
    def _generate_initial_assessment(self, search_results: List[SearchResult]) -> str:
        """Generate initial assessment steps"""
        assessment = []
        for result in search_results[:2]:
            if "check" in result.text.lower() or "verify" in result.text.lower():
                # Extract check/verify steps
                text = result.text
                sentences = text.split(".")
                for sentence in sentences:
                    if "check" in sentence.lower() or "verify" in sentence.lower():
                        assessment.append(f"- {sentence.strip()}")
                        break
        
        if not assessment:
            assessment = [
                "- Check system status and logs",
                "- Verify resource utilization",
                "- Confirm network connectivity"
            ]
        
        return "\n".join(assessment[:3])
    
    def _extract_diagnostic_commands(self, search_results: List[SearchResult]) -> str:
        """Extract diagnostic commands from search results"""
        commands = []
        for result in search_results:
            text = result.text.lower()
            if "ping" in text or "traceroute" in text or "top" in text or "htop" in text:
                if "ping" in text:
                    commands.append("ping -c 4 <target_host>")
                if "traceroute" in text:
                    commands.append("traceroute <target_host>")
                if "top" in text or "htop" in text:
                    commands.append("top")
                    commands.append("htop")
        
        if not commands:
            commands = [
                "ping -c 4 <target_host>",
                "traceroute <target_host>",
                "top",
                "df -h",
                "free -m"
            ]
        
        return "\n".join(commands[:5])
    
    def _generate_resolution_steps(self, search_results: List[SearchResult]) -> str:
        """Generate resolution steps from search results"""
        steps = []
        for result in search_results[:3]:
            text = result.text
            sentences = text.split(".")
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in ["restart", "fix", "resolve", "update", "configure"]):
                    steps.append(f"- {sentence.strip()}")
                    break
        
        if not steps:
            steps = [
                "- Restart the affected service",
                "- Check and update configuration if needed",
                "- Verify all dependencies are running"
            ]
        
        return "\n".join(steps[:4])
    
    def _generate_verification_steps(self, search_results: List[SearchResult]) -> str:
        """Generate verification steps"""
        return """- Verify the issue is resolved
- Check system logs for any errors
- Monitor system performance for 15 minutes
- Confirm all services are running normally"""
    
    def _generate_prevention_measures(self, search_results: List[SearchResult]) -> str:
        """Generate prevention measures"""
        return """- Implement monitoring and alerting
- Regular system maintenance and updates
- Document configuration changes
- Set up automated backups"""
    
    def _generate_references(self, search_results: List[SearchResult]) -> str:
        """Generate reference links"""
        references = []
        for i, result in enumerate(search_results, 1):
            references.append(f"{i}. {result.document_title} (Score: {result.score:.3f})")
        return "\n".join(references)
    
    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence score based on search results"""
        if not search_results:
            return 0.3  # Low confidence if no results
        
        # Base confidence on top result score
        top_score = search_results[0].score
        
        # Adjust based on number of results
        result_count_factor = min(len(search_results) / 5.0, 1.0)
        
        # Calculate final confidence
        confidence = (top_score * 0.7) + (result_count_factor * 0.3)
        
        return min(confidence, 0.95)  # Cap at 95%
    
    def _sanitize_description_field(self, yaml_content: str) -> str:
        """Clean up description fields that LLMs sometimes corrupt.
        
        Common issues:
        - Adding junk text like "Service: server" after the description
        - Including extra colons in descriptions
        """
        if not yaml_content:
            return yaml_content
        
        lines = yaml_content.split("\n")
        sanitized_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check if this is a description line
            if stripped.startswith("description:") and ":" in stripped:
                # Extract the value part
                parts = stripped.split("description:", 1)
                if len(parts) > 1:
                    value = parts[1].strip()
                    
                    # Remove common patterns that LLMs add incorrectly
                    # Pattern: "text. Service: service" should become just "text"
                    value = re.sub(r'\s*\.?\s*Service:\s*\w+\s*\.?$', '', value, flags=re.IGNORECASE)
                    value = re.sub(r'\s*\.?\s*Environment:\s*\w+\s*\.?$', '', value, flags=re.IGNORECASE)
                    value = re.sub(r'\s*\.?\s*Env:\s*\w+\s*\.?$', '', value, flags=re.IGNORECASE)
                    
                    # Reconstruct the line
                    sanitized_lines.append("description: " + value)
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)
        
        return "\n".join(sanitized_lines)

    def _generate_fallback_content(self, issue: str) -> str:
        """Generate fallback content when no search results"""
        return f"""# Troubleshooting Runbook

## Issue Description
{issue}

## Root Cause Analysis
Unable to find specific information about this issue in the knowledge base.

## Troubleshooting Steps

### Step 1: Initial Assessment
- Check system status and logs
- Verify resource utilization
- Confirm network connectivity

### Step 2: Diagnostic Commands
```bash
ping -c 4 <target_host>
traceroute <target_host>
top
df -h
free -m
```

### Step 3: Resolution Steps
- Review system logs for error messages
- Check configuration files
- Restart affected services
- Verify all dependencies are running

### Step 4: Verification
- Verify the issue is resolved
- Check system logs for any errors
- Monitor system performance

## Prevention Measures
- Implement monitoring and alerting
- Regular system maintenance
- Document configuration changes

---
*This runbook was generated with limited knowledge base information. Manual review required.*
"""