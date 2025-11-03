"""
Seed realistic demo scenarios for demonstrations

This script creates 5-6 realistic IT troubleshooting scenarios with
pre-generated, approved runbooks for showcasing the Assistant Mode.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.models.runbook import Runbook
from app.models.execution import Execution
from app.models.audit import Audit
from app.models.system_config import SystemConfig
from app.models.runbook_usage import RunbookUsage
from app.models.runbook_similarity import RunbookSimilarity
from app.models.runbook_citation import RunbookCitation
from app.services.runbook_parser import RunbookParser


DEMO_SCENARIOS = [
    {
        "title": "Resolve High CPU Usage on Web Server",
        "description": "Production web server CPU usage at 95% causing slow response times",
        "yaml_content": """runbook_id: rb-demo-cpu-001
version: "1.0"
title: Resolve High CPU Usage on Web Server
service: server
env: prod
risk: medium
description: Diagnostic and resolution steps for high CPU usage on production web server
owner: IT Operations
last_tested: "2025-11-01"
review_required: false
inputs: []
prechecks:
  - description: Verify server connectivity
    command: ping -c 2 web-prod-01
    expected_output: "2 packets transmitted, 0 packet loss"
  - description: Check current CPU usage
    command: top -b -n 1 | head -20
    expected_output: "Load average values and top CPU consuming processes"
steps:
  - name: Identify CPU-intensive processes
    type: command
    command: ps aux --sort=-%cpu | head -10
    description: List top CPU-consuming processes
    expected_output: "List of processes with CPU percentages"
    severity: safe
  - name: Check system load
    type: command
    command: uptime
    description: Display system load averages
    expected_output: "Load average for 1, 5, 15 minutes"
    severity: safe
  - name: Check for runaway processes
    type: command
    command: ps aux | awk '$3 > 50.0 {print $0}'
    description: Find processes using more than 50% CPU
    expected_output: "List of high-CPU processes or empty if none"
    severity: safe
  - name: Restart overloaded service
    type: command
    command: systemctl restart nginx
    description: Restart web server to clear stuck connections
    expected_output: "Service restarted successfully"
    severity: moderate
postchecks:
  - description: Verify CPU returned to normal
    command: top -b -n 1 | grep "Cpu(s)"
    expected_output: "CPU usage below 20%"
  - description: Confirm web service responding
    command: curl -I http://localhost
    expected_output: "HTTP 200 OK response"
"""
    },
    {
        "title": "Fix Database Connection Pool Exhausted",
        "description": "Application unable to connect to database due to exhausted connection pool",
        "yaml_content": """runbook_id: rb-demo-db-001
version: "1.0"
title: Fix Database Connection Pool Exhausted
service: database
env: prod
risk: high
description: Resolve exhausted database connection pool preventing application connections
owner: Database Team
last_tested: "2025-11-01"
review_required: true
inputs: []
prechecks:
  - description: Check database server status
    command: systemctl status postgresql
    expected_output: "Active: active (running)"
  - description: Verify port is listening
    command: netstat -tlnp | grep :5432
    expected_output: "tcp LISTEN on port 5432"
steps:
  - name: Check current connections
    type: command
    command: psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE datname='prod_db';"
    description: Count active database connections
    expected_output: "Connection count (current)"
    severity: safe
  - name: List all connections
    type: command
    command: psql -U postgres -c "SELECT pid, usename, application_name, client_addr, state FROM pg_stat_activity WHERE datname='prod_db';"
    description: Display all active connections
    expected_output: "List of active connections"
    severity: safe
  - name: Terminate idle connections
    type: command
    command: psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='prod_db' AND state='idle' AND state_change < now() - interval '1 hour';"
    description: Kill idle connections older than 1 hour
    expected_output: "Connections terminated"
    severity: moderate
  - name: Increase max connections
    type: command
    command: psql -U postgres -c "ALTER SYSTEM SET max_connections = 200; SELECT pg_reload_conf();"
    description: Increase max connections limit
    expected_output: "Configuration reloaded"
    severity: moderate
postchecks:
  - description: Verify connection pool has capacity
    command: psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE datname='prod_db';"
    expected_output: "Connection count below 80% of max"
  - description: Test application connectivity
    command: curl -f http://app-host:8080/health
    expected_output: "Application responding"
"""
    },
    {
        "title": "Resolve Disk Space Critical on /var Partition",
        "description": "Critical disk space alert on /var partition threatening system stability",
        "yaml_content": """runbook_id: rb-demo-disk-001
version: "1.0"
title: Resolve Disk Space Critical on /var Partition
service: storage
env: prod
risk: high
description: Free up disk space on /var partition to prevent system failure
owner: Infrastructure Team
last_tested: "2025-11-01"
review_required: true
inputs: []
prechecks:
  - description: Check current disk usage
    command: df -h /var
    expected_output: "Current disk usage percentage"
  - description: Identify largest directories
    command: du -sh /var/* | sort -rh | head -10
    expected_output: "Top 10 directories by size"
steps:
  - name: Clean old log files
    type: command
    command: journalctl --vacuum-time=7d
    description: Remove system journal logs older than 7 days
    expected_output: "Old logs deleted"
    severity: safe
  - name: Clean package cache
    type: command
    command: apt-get clean && apt-get autoremove -y
    description: Remove cached packages and unused dependencies
    expected_output: "Cache cleared"
    severity: moderate
  - name: Rotate old application logs
    type: command
    command: find /var/log/apps -name "*.log" -mtime +30 -delete
    description: Delete application logs older than 30 days
    expected_output: "Old logs removed"
    severity: moderate
  - name: Compress old logs
    type: command
    command: find /var/log -name "*.log" -size +100M -exec gzip {} \\;
    description: Compress large log files to save space
    expected_output: "Files compressed"
    severity: moderate
postchecks:
  - description: Verify space freed
    command: df -h /var
    expected_output: "Disk usage below 80%"
  - description: Confirm services still running
    command: systemctl status nginx postgresql
    expected_output: "All services active"
"""
    },
    {
        "title": "Fix Memory Leak in Java Application",
        "description": "Java application memory consumption continuously increasing causing OOM errors",
        "yaml_content": """runbook_id: rb-demo-mem-001
version: "1.0"
title: Fix Memory Leak in Java Application
service: web
env: prod
risk: high
description: Diagnose and resolve memory leak in Java application causing OutOfMemory errors
owner: Application Team
last_tested: "2025-11-01"
review_required: true
inputs: []
prechecks:
  - description: Check current memory usage
    command: free -h
    expected_output: "Memory usage statistics"
  - description: Verify application is running
    command: systemctl status java-app
    expected_output: "Active: active (running)"
steps:
  - name: Find Java processes
    type: command
    command: ps aux | grep java | grep -v grep
    description: List all Java processes with memory usage
    expected_output: "Java process list"
    severity: safe
  - name: Dump heap for analysis
    type: command
    command: jmap -dump:live,format=b,file=/tmp/heap.dump $(pidof java)
    description: Create heap dump for leak analysis
    expected_output: "Heap dump created"
    severity: safe
  - name: Check GC statistics
    type: command
    command: jstat -gc $(pidof java) 1000 5
    description: Monitor garbage collection activity
    expected_output: "GC statistics"
    severity: safe
  - name: Increase heap size temporarily
    type: command
    command: systemctl restart java-app && echo "-Xmx4096m" >> /etc/java-app/jvm.conf
    description: Increase heap size from 2GB to 4GB
    expected_output: "Service restarted with new heap size"
    severity: moderate
postchecks:
  - description: Monitor memory after restart
    command: watch -n 1 'ps aux | grep java | grep -v grep'
    expected_output: "Memory stable or decreasing"
  - description: Verify application functionality
    command: curl -f http://app-host:8080/api/health
    expected_output: "Application healthy"
"""
    },
    {
        "title": "SSL Certificate Expiring Soon",
        "description": "SSL certificate for production domain expires in 3 days",
        "yaml_content": """runbook_id: rb-demo-ssl-001
version: "1.0"
title: Renew SSL Certificate Expiring Soon
service: network
env: prod
risk: low
description: Renew SSL certificate before expiration to avoid service disruption
owner: Security Team
last_tested: "2025-11-01"
review_required: false
inputs:
  - name: domain
    type: string
    required: true
    description: Domain name requiring certificate renewal
prechecks:
  - description: Check current certificate expiration
    command: openssl s_client -connect example.com:443 -servername example.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
    expected_output: "Certificate validity dates"
  - description: Verify certificate installation
    command: ls -la /etc/ssl/certs/prod-cert.*
    expected_output: "Certificate files present"
steps:
  - name: Request new certificate
    type: command
    command: certbot renew --cert-name {domain} --force-renewal
    description: Request SSL certificate renewal
    expected_output: "Certificate renewed successfully"
    severity: safe
  - name: Verify certificate chain
    type: command
    command: openssl x509 -in /etc/letsencrypt/live/{domain}/fullchain.pem -noout -text | grep -A 2 "Validity"
    description: Check new certificate validity period
    expected_output: "New expiration date in future"
    severity: safe
  - name: Restart web server
    type: command
    command: systemctl reload nginx
    description: Reload web server with new certificate
    expected_output: "Nginx reloaded"
    severity: moderate
postchecks:
  - description: Test certificate renewal
    command: openssl s_client -connect {domain}:443 -servername {domain} < /dev/null 2>/dev/null | openssl x509 -noout -dates
    expected_output: "Certificate valid for 60+ days"
  - description: Verify HTTPS access
    command: curl -I https://{domain}
    expected_output: "HTTP 200 OK"
"""
    },
    {
        "title": "API Rate Limit Reached",
        "description": "Third-party API rate limit exceeded causing application failures",
        "yaml_content": """runbook_id: rb-demo-api-001
version: "1.0"
title: Handle API Rate Limit Exceeded
service: web
env: prod
risk: medium
description: Manage and prevent API rate limit issues with external services
owner: DevOps Team
last_tested: "2025-11-01"
review_required: false
inputs:
  - name: api_key
    type: string
    required: true
    description: API key for rate limit checking
prechecks:
  - description: Check current API usage
    command: "curl -H 'Authorization: Bearer {api_key}' https://api.external.com/v1/usage"
    expected_output: "Current usage statistics"
  - description: Verify API status
    command: curl -f https://status.external.com/api
    expected_output: "API operational"
steps:
  - name: Check rate limit headers
    type: command
    command: "curl -I -H 'Authorization: Bearer {api_key}' https://api.external.com/v1/test | grep -i rate-limit"
    description: View rate limit headers from API
    expected_output: "Rate limit headers"
    severity: safe
  - name: Implement request queue
    type: command
    command: 'redis-cli LPUSH api-queue "task1 task2 task3"'
    description: Queue pending requests to avoid burst
    expected_output: "Requests queued"
    severity: safe
  - name: Switch to backup API key
    type: command
    command: "kubectl set env deployment/app EXTERNAL_API_KEY={backup_api_key}"
    description: Rotate to backup API credentials
    expected_output: "Environment updated"
    severity: moderate
postchecks:
  - description: Verify API calls succeeding
    command: tail -f /var/log/app/api.log | grep "API_SUCCESS"
    expected_output: "Successful API calls"
  - description: Monitor rate limit
    command: "watch -n 5 'curl -H Authorization: Bearer {api_key} https://api.external.com/v1/usage'"
    expected_output: "Usage within limits"
"""
    }
]


def seed_demo_scenarios():
    """Seed demo scenarios into database"""
    db: Session = SessionLocal()
    
    try:
        # Count existing demo runbooks
        existing_count = db.query(Runbook).filter(
            Runbook.tenant_id == 1,
            Runbook.title.like("Runbook: %")
        ).count()
        
        print(f"Found {existing_count} existing runbooks in demo tenant")
        
        # Create markdown body for each scenario
        import yaml
        for idx, scenario in enumerate(DEMO_SCENARIOS, 1):
            yaml_content = scenario["yaml_content"]
            
            # First, try to parse YAML to validate it
            try:
                spec = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                print(f"Invalid YAML in scenario {idx}: {e}")
                continue
            
            # Create markdown body with YAML code fence
            body_md = f"""# Agent Runbook (YAML)

```yaml
{yaml_content}
```
"""
            
            # Check if runbook already exists
            existing = db.query(Runbook).filter(
                Runbook.tenant_id == 1,
                Runbook.title == f"Runbook: {spec['title']}"
            ).first()
            
            if existing:
                print(f"Skipping {spec['title']} - already exists")
                continue
            
            # Create runbook entry
            runbook = Runbook(
                tenant_id=1,
                title=f"Runbook: {spec['title']}",
                body_md=body_md,
                meta_data=json.dumps({
                    "issue_description": scenario["description"],
                    "generated_by": "demo_seed",
                    "service": spec.get("service", ""),
                    "env": spec.get("env", ""),
                    "risk": spec.get("risk", ""),
                    "runbook_spec": spec,
                    "generation_mode": "demo_seeded"
                }),
                confidence=0.85,
                status="approved",
                is_active="active"
            )
            
            db.add(runbook)
            print(f"Added runbook: {spec['title']}")
        
        db.commit()
        print("Demo scenarios seeded successfully")
        
        # Display summary
        total_count = db.query(Runbook).filter(Runbook.tenant_id == 1).count()
        approved_count = db.query(Runbook).filter(
            Runbook.tenant_id == 1,
            Runbook.status == "approved"
        ).count()
        
        print(f"Total runbooks in demo tenant: {total_count}")
        print(f"Approved runbooks: {approved_count}")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding demo scenarios: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_scenarios()

