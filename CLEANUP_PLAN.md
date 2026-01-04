# Code Cleanup Plan

## Phase 1: File Cleanup (Disk Space)

### Markdown Files to DELETE (Temporary Fix Guides - 50+ files)
These were created during troubleshooting and are no longer needed:

**Dev Environment Setup (Temporary):**
- BUILD_DEV_FRONTEND.md
- FIX_DEV_CONTAINERCONFIG.md
- CREATE_DEV_ADMIN.md
- VERIFY_DEV_ENVIRONMENT.md
- START_DEV_SERVICES.md
- SETUP_DEV_DATABASE.md
- FIX_DEV_TABLES.md
- MANUAL_DEV_SETUP.md
- QUICK_START_DEV.md
- FIX_DEV_DOCKER_COMPOSE.md
- QUICK_FIX_DEV_SETUP.md
- DEPLOY_DEV_ENVIRONMENT.md
- CHECK_DEV_BACKEND.md
- SETUP_BOTH_ENVIRONMENTS.md

**Production Fix Guides (Temporary):**
- FIX_PRODUCTION_CONTAINERCONFIG.md
- FIX_PROD_AND_DEV.md
- FIXES_APPLIED.md
- DEV_PROD_INTERACTION_REVIEW.md

**Implementation Summaries (Completed):**
- LICENSING_IMPLEMENTATION_SUMMARY.md
- CODE_CLEANUP_SUMMARY.md
- BILLING_IMPLEMENTATION_SUMMARY.md
- IMPLEMENTATION_SUMMARY.md
- OVERNIGHT_CLEANUP_PROGRESS.md
- CODE_CLEANUP_PROGRESS.md
- OVERNIGHT_WORK_COMPLETED.md
- P0_SECURITY_FIXES_COMPLETED.md
- PHASE_1_2_STATUS_REPORT.md

**Troubleshooting Guides (One-off):**
- LOGIN_TROUBLESHOOTING.md
- BACKEND_STARTUP_ISSUES.md
- TROUBLESHOOT_POWERSHELL.md
- POWERSHELL_FIREWALL_FIX.md
- MALWARE_REMOVAL_GUIDE.md
- CURSOR_AI_TOOL_BLOCKING.md

**Quick Start/Deploy Guides (Redundant):**
- QUICK_DEPLOY_20MIN.md
- QUICK_DEPLOYMENT_GUIDE.md
- DEPLOYMENT_QUICK_START.md
- DEPLOYMENT_PLAN.md
- README_DEPLOYMENT.md

**ServiceNow Test Guides (Temporary):**
- POSTMAN_SERVICENOW_CONNECTION_TEST.md
- POSTMAN_SERVICENOW_TEST.md
- TEST_SERVICENOW_CONNECTION.md
- SERVICENOW_RESOLVE_INCIDENT_POSTMAN.md

**Role/Tenant Fix Summaries (Completed):**
- ROLE_FIX_SUMMARY.md
- ROLE_ANALYSIS.md
- TENANT_SEPARATION_FIX.md
- TENANT_SEPARATION_ISSUES.md

**Other Temporary:**
- CODE_CLEANUP_PLAN.md
- CODE_REVIEW_STATUS_ANALYSIS.md
- PROJECT_STATUS_AND_NEXT_STEPS.md
- PRODUCTION_READINESS_ASSESSMENT.md
- ENVIRONMENT_DIFFERENCES.md
- FITGLIDE_SETUP_ANALYSIS.md
- PORT_COEXISTENCE_GUIDE.md
- GENERATE_KEYS_INSTRUCTIONS.md
- QUICK_KEY_GENERATION.md

### Markdown Files to KEEP (Important Documentation)
- ARCHITECTURE.md ⭐ (User specified to keep)
- ALERTS_VS_TICKETS_ARCHITECTURE.md
- MONITORING_CONNECTORS_ARCHITECTURE.md
- PHASE2_AGENT_ARCHITECTURE.md
- PHASES.md
- PHASE2_WORKER_ORCHESTRATION_SPEC.md
- SERVICENOW_INTEGRATION_SETUP.md (Active integration)
- SERVICENOW_SERVICE_ACCOUNT_SETUP.md (Active integration)
- AZURE_MONITOR_SETUP_GUIDE.md (Active integration)
- PROMETHEUS_SETUP_GUIDE.md (Active integration)
- MONITORING_WEBHOOKS_SETUP.md (Active integration)
- SUPER_ADMIN_SETUP.md (Active feature)
- ADMIN_LOGIN_GUIDE.md (Active feature)
- SECURITY_HARDENING_GUIDE.md (Security)
- PAAS_DEPLOYMENT_GUIDE.md (Deployment)
- NETWORK_DEVICE_MANAGEMENT.md (Active feature)

### Scripts to DELETE (One-off Fixes - 30+ files)

**Docker Fix Scripts (Temporary):**
- scripts/fix-docker-complete.sh
- scripts/fix-docker-compose-error.sh
- scripts/fix-docker-compose-structure.sh
- scripts/fix-docker-daemon-quick.sh
- scripts/fix-docker-timeout.sh
- scripts/fix-docker-build-lease-error.sh
- scripts/fix-all-docker-containers.sh
- scripts/fix-backend-containerconfig.sh
- scripts/fix-postgres-port-conflict.sh
- scripts/fix-port-conflict.sh
- scripts/quick-fix-port-5432.sh
- scripts/switch-to-production-compose.sh
- scripts/clean-switch-to-production.sh
- scripts/docker-troubleshoot.sh
- fix-docker-complete.sh
- fix-docker-containers.sh

**Super Admin Fix Scripts (Temporary):**
- scripts/fix-super-admin-endpoints.sh
- scripts/test-super-admin-endpoints.sh

**Check Scripts (Temporary):**
- scripts/check-docker-state.sh
- scripts/check-fitglide-setup.sh
- scripts/check-poller-activity.sh
- scripts/check-servicenow-sync.sh
- scripts/check-cpu-usage.sh
- scripts/check-suspicious-processes.sh
- scripts/check-backend-health.sh
- check-frontend-build.sh
- check-memory.sh
- check-license-plans-production.sh

**Security Scripts (One-off):**
- scripts/secure-server.sh
- scripts/remove-malware.sh
- scripts/detect-malware.sh
- one_shot_miner_cleanup.sh

**Migration Scripts (Completed):**
- scripts/apply-license-plan-migration.sh
- scripts/create-docker-network.sh
- run-migration-role-id.sh

**Other Temporary:**
- scripts/start-services-slow.sh
- scripts/run_dr_checklist.sh
- test_setup.sh
- setup_complete.sh
- start-llm-optimized.sh
- verify-license-plans-ui.sh

### Scripts to KEEP (Active/Useful)
- scripts/backup-production.sh
- scripts/backup-demo-data.sh
- scripts/restore-demo-data.sh
- scripts/deploy-production.sh
- scripts/deploy-dev.sh
- scripts/quick-deploy.sh
- scripts/setup-server.sh
- scripts/setup-paas.sh
- scripts/sandbox-start.sh
- scripts/sandbox-stop.sh
- scripts/sandbox-reset.sh

### PowerShell Scripts to DELETE (Test/One-off - 20+ files)
- All test-*.ps1 files (test-azure-*, test-datadog-*, test-prometheus-*, test-servicenow-*, test-splunk-*, test-ollama-*, test-approval.ps1)
- All check-*.ps1 files (check-connection.py, check-credential.ps1, check-datadog-monitors.ps1, etc.)
- All cleanup-*.ps1/sql files
- associate-runbook-5-to-ticket-31.ps1
- check_ticket-31.ps1
- count_lines*.ps1/py
- debug-execution-flow.ps1
- diagnose-manageengine-connection.ps1
- get-manageengine-*.ps1
- quick_check.ps1
- restart-backend.ps1
- run-cleanup.ps1
- sync-servicenow-tickets.ps1
- trigger-servicenow-sync.ps1
- update-servicenow-credentials.ps1
- verify-azure-subscription.ps1

### Python Scripts to DELETE (Test/One-off)
- check_user.py
- check-connection.py
- check-servicenow-connection.py
- test-manageengine-connection.py
- test-servicenow-connection.py
- test-servicenow-postman-format.py
- check_new_connection.ps1
- check_refresh_token_status.ps1
- check_msp_users.py
- count_lines*.py
- status_dashboard.py
- generate-encryption-key.py

### Test Files to DELETE
- azure_test_payload.json
- datadog_test_payload.json
- prometheus_test_payload.json
- test_results.json
- tickets_sample.csv

## Phase 2: Code Quality Improvements

1. **Linting & Formatting**
   - Run black/isort on all Python files
   - Fix TypeScript/ESLint errors
   - Remove unused imports
   - Fix type errors

2. **Remove Dead Code**
   - Unused functions/classes
   - Commented-out code
   - Debug print statements
   - TODO comments that are completed

3. **Improve Documentation**
   - Add docstrings to functions
   - Update README files
   - Document API endpoints

4. **Refactor**
   - Extract duplicate code
   - Improve error handling
   - Standardize naming conventions

## Phase 3: App Connections (After Cleanup)

1. Review existing integrations
2. Add new app connections
3. Test integrations

