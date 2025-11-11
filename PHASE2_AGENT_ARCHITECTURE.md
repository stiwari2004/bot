# Human-in-the-Loop Agent Architecture
## Phase 2: Enterprise-Grade Autonomous Troubleshooting Agent

## Executive Summary

This document defines the architecture for Phase 2: Human-in-the-Loop Agent, which enables automated runbook execution with human validation. The architecture is designed to be **robust, secure, and enterprise-grade**, supporting integration with monitoring tools, infrastructure components, and enterprise security systems.

---

## 1. System Overview

### 1.1 Vision

The agent receives tickets from monitoring tools, analyzes them for false positives, executes runbooks with human validation, and either resolves issues or escalates when needed.

### 1.2 Key Requirements

- **Ticket Analysis**: Automatically detect false positives vs true positives
- **Runbook Execution**: Execute approved runbooks with human validation at each step
- **Infrastructure Access**: Secure connections to servers, databases, APIs, cloud services
- **Resolution Verification**: Automatically verify if issues are resolved
- **Escalation**: Escalate to human operators when automation fails
- **Alert Suppression**: Automatically suppress false positive alerts
- **Enterprise Security**: Credential vault, audit logging, RBAC, compliance

---

## 2. Architecture Components

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Tools                              │
│  (Prometheus, Datadog, New Relic, PagerDuty, Custom)            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Ticket Ingestion Layer                        │
│  - Webhook Receiver                                              │
│  - Message Queue (RabbitMQ/Kafka)                               │
│  - Ticket Normalization                                          │
│  - Rate Limiting & Throttling                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Ticket Analysis Engine                        │
│  - False Positive Detection (LLM-based)                          │
│  - True Positive Classification                                  │
│  - Severity Assessment                                           │
│  - Duplicate Detection                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐         ┌──────────────────────┐
│ False Positive   │         │ True Positive        │
│ - Close Ticket   │         │ - Continue Flow      │
│ - Suppress Alert │         │ - Execute Runbook    │
└──────────────────┘         └──────────┬───────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Runbook Resolution Engine                     │
│  - Semantic Search for Existing Runbook                         │
│  - Runbook Match Scoring                                         │
│  - Confidence Threshold Check                                    │
│  - Generate New Runbook (if no match)                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐         ┌──────────────────────┐
│ Existing Runbook │         │ No Runbook Found      │
│ Execute          │         │ Generate & Queue      │
└────────┬─────────┘         └──────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Human-in-the-Loop Execution Engine           │
│  - Step-by-Step Execution                                        │
│  - Human Validation Checkpoints                                  │
│  - Command Execution (SSH/API/CLI)                               │
│  - Output Capture & Analysis                                     │
│  - Rollback Capability                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Resolution Verification                       │
│  - Postcheck Execution                                           │
│  - Issue Resolution Confirmation                                 │
│  - Success Metrics Collection                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐         ┌──────────────────────┐
│ Issue Resolved   │         │ Issue Not Resolved    │
│ - Close Ticket   │         │ - Escalate to Human   │
│ - Update Metrics │         │ - Log Failure         │
│ - Suppress Alert │         │ - Create Alert        │
└──────────────────┘         └──────────────────────┘
```

---

## 3. Core Components

### 3.1 Ticket Ingestion Service

**Purpose**: Receive and normalize tickets from various monitoring tools

**Note**: Ticketing tools (ServiceNow, Jira, PagerDuty) already have their own real-time broadcasting mechanisms. We do not duplicate this functionality. Our system focuses on ticket ingestion, processing, and status updates back to the ticketing tool via their APIs.

**Components**:
- **Webhook Receiver**: HTTPS endpoint for webhook-based integrations (push-based)
- **Polling Adapters**: For monitoring tools that don't support webhooks (pull-based, configurable intervals)
- **Message Queue**: RabbitMQ/Kafka for reliable message processing and buffering
- **Ticket Normalizer**: Convert various formats to standard ticket schema
- **Rate Limiter**: Prevent system overload
- **Status Update Client**: Update ticket status back to ticketing tool via their API

**Processing Flow**:
```
Monitoring Tool → Webhook/Polling → Message Queue → Real-time Processor
                                                    ↓
                                    ┌───────────────┴───────────────┐
                                    │                               │
                              Analysis Engine              Update Ticketing Tool
                                    │                               │ (via API)
                                    ↓                               ↓
                            Update Ticket Status         → Status Sync to ServiceNow/Jira
```

**Features**:
- **Immediate Processing**: Tickets processed within seconds of receipt
- **Status Synchronization**: Update ticket status back to ticketing tool via their API
- **No Redundant Broadcasting**: We rely on ticketing tool's native real-time features

**Update Mechanisms**:
- **Status Updates**: Update ticket status via ticketing tool's API (ServiceNow REST API, Jira API, etc.)
- **Execution Progress**: Update ticket comments/notes with execution progress
- **Resolution Status**: Mark tickets as resolved/escalated via ticketing tool API

**Security**:
- API authentication (API keys, OAuth2)
- IP whitelisting
- Request signing verification
- Rate limiting per source
- Mutual TLS (mTLS) for API calls to ticketing tools

**Schema**:
```python
class Ticket:
    id: str                    # Unique ticket ID
    source: str                # Monitoring tool name
    title: str
    description: str
    severity: str             # critical, high, medium, low
    environment: str          # prod, staging, dev
    service: str              # Service/component name
    metadata: dict            # Tool-specific metadata
    received_at: datetime
    raw_payload: dict         # Original payload for audit
```

---

### 3.2 Ticket Analysis Engine

**Purpose**: Determine if ticket is false positive or true positive

**Components**:
- **LLM Analyzer**: Use LLM to analyze ticket description
- **Pattern Matcher**: Match against known false positive patterns
- **Historical Analysis**: Check if similar tickets were false positives
- **Classification Service**: Return classification with confidence

**Flow**:
```
Ticket → LLM Analysis → Pattern Matching → Historical Check → Classification
                                                              ├─ False Positive (confidence > 0.8)
                                                              └─ True Positive (confidence > 0.8)
                                                              └─ Uncertain (confidence ≤ 0.8) → Human Review Queue
```

**LLM Prompt Template**:
```
Analyze the following monitoring alert/ticket and determine if it's a false positive or a true positive.

False Positive Indicators:
- Expected behavior (scheduled maintenance, backups, etc.)
- Known issues already acknowledged
- Configuration changes that are intentional
- Test/debugging activities

True Positive Indicators:
- Unexpected errors or failures
- Performance degradation
- Service unavailability
- Data corruption or loss

Ticket Details:
{title}
{description}
{metadata}

Provide:
1. Classification: false_positive | true_positive | uncertain
2. Confidence: 0.0 - 1.0
3. Reasoning: Detailed explanation
```

**Output**:
```python
class TicketAnalysis:
    ticket_id: str
    classification: str        # false_positive | true_positive | uncertain
    confidence: float          # 0.0 - 1.0
    reasoning: str
    false_positive_patterns_matched: List[str]
    requires_human_review: bool
    analyzed_at: datetime
```

---

### 3.3 Runbook Resolution Engine

**Purpose**: Find or generate appropriate runbook for the issue

**Components**:
- **Semantic Search**: Search existing runbooks using RAG
- **Match Scorer**: Score runbook matches using confidence scoring
- **Threshold Checker**: Determine if match is sufficient
- **Runbook Generator**: Generate new runbook if no match found

**Flow**:
```
Ticket → Semantic Search → Match Scoring → Threshold Check
                                              ├─ Match Found (confidence ≥ 0.7)
                                              │   └─ Use Existing Runbook
                                              └─ No Match (confidence < 0.7)
                                                  └─ Generate New Runbook (Phase 1)
```

**Match Scoring**:
- Semantic similarity: 40%
- Issue type match: 30%
- Environment match: 20%
- Service match: 10%

**Decision Matrix**:
- **Confidence ≥ 0.8**: Auto-use runbook (with human notification)
- **Confidence 0.7-0.8**: Request human approval before execution
- **Confidence < 0.7**: Generate new runbook or escalate

---

### 3.4 Human-in-the-Loop Execution Engine

**Purpose**: Execute runbooks with human validation checkpoints using distributed agent workers

**Components**:
- **Execution Orchestrator**: Manages execution flow, coordinates with agent workers
- **Agent Worker Manager**: Manages agent worker pool, selects appropriate worker
- **Command Executor**: Executes commands via agent workers (SSH/API/CLI)
- **Validation Checkpoint Manager**: Handles human approval points
- **Output Analyzer**: Analyzes command outputs
- **Rollback Manager**: Executes rollback procedures
- **Execution Event Publisher**: Publishes execution events internally (for UI, not external broadcast)

**Note**: Execution progress updates are sent internally to our UI for human operators. Final status updates are sent back to ticketing tools via their APIs. We do not duplicate ticketing tool broadcasting mechanisms.

**Execution Flow**:
```
1. Prechecks Phase
   ├─ Orchestrator selects agent worker
   ├─ Worker retrieves credentials from vault
   ├─ Worker establishes connection to infrastructure
   ├─ Execute all prechecks sequentially
   ├─ Capture outputs and stream to orchestrator
   ├─ Real-time status update via WebSocket
   ├─ Human Validation Checkpoint ⚠️
   └─ Continue if approved

2. Main Steps Phase
   ├─ For each step:
   │   ├─ Orchestrator sends command to worker
   │   ├─ Worker executes command
   │   ├─ Capture output (real-time streaming)
   │   ├─ Analyze output for errors
   │   ├─ Real-time status update via WebSocket
   │   ├─ Human Validation Checkpoint ⚠️ (if configured)
   │   └─ Continue if approved
   └─ Stop on error or human rejection

3. Postchecks Phase
   ├─ Execute all postchecks
   ├─ Verify resolution
   ├─ Real-time status update via WebSocket
   ├─ Human Validation Checkpoint ⚠️
   └─ Confirm resolution

4. Resolution Verification
   ├─ Run final verification checks
   ├─ Confirm issue resolved
   └─ Update ticket status (real-time update)
```

**Human Validation Checkpoints**:
- **Before First Precheck**: Approve to start troubleshooting
- **After Prechecks**: Review precheck results before proceeding
- **Before Each Critical Step**: Approve potentially destructive actions
- **After All Steps**: Review before final verification
- **Before Resolution**: Confirm issue is resolved

**Configuration**:
```yaml
validation_mode: "per_step" | "per_phase" | "critical_only" | "final_only"
critical_steps: ["database_shutdown", "service_restart", "data_deletion"]
auto_approve_threshold: 0.95  # Auto-approve if confidence > 0.95
```

---

### 3.5 Infrastructure Connector Layer

**Purpose**: Secure connections to infrastructure components with enterprise-grade access patterns

**Architecture Decision: Distributed Agent Workers**

**❌ VS Code-like Approach (Rejected)**:
- VS Code Remote SSH requires manual connection establishment
- Not suitable for automated execution
- Requires user context and interactive sessions
- Difficult to scale and manage at enterprise level

**✅ Distributed Agent Worker Approach (Selected)**:
- **Agent Workers**: Separate worker processes/nodes that execute commands
- **Central Orchestrator**: Coordinates execution from application server
- **Network-Aware**: Agent workers can be deployed closer to infrastructure
- **Scalable**: Multiple workers can handle concurrent executions
- **Secure**: Workers authenticate independently, no user context needed

**Infrastructure Access Patterns**:

**Pattern 1: Direct Network Access (Same Network Segment)**
```
Application Server → Agent Worker → Infrastructure Component
                      (Same VPC/DMZ)
```
- **Use Case**: Cloud environments, internal networks
- **Security**: VPC security groups, network ACLs
- **Performance**: Low latency, direct connections

**Pattern 2: Bastion/Jump Host (Network Segmentation)**
```
Application Server → Agent Worker → Bastion Host → Target Infrastructure
                      (DMZ)          (Jump Host)    (Private Network)
```
- **Use Case**: Production environments with strict network segmentation
- **Security**: SSH tunneling through bastion, IP whitelisting
- **Performance**: Additional hop, but necessary for security

**Pattern 3: VPN/Tunnel (Cross-Network Access)**
```
Application Server → Agent Worker → VPN Gateway → Remote Infrastructure
                      (On-prem)                    (Cloud/Remote)
```
- **Use Case**: Hybrid cloud, on-premises to cloud connections
- **Security**: VPN encryption, certificate-based authentication
- **Performance**: Latency depends on VPN quality

**Pattern 4: Agent Pod/Container (Kubernetes/Container Environments)**
```
Application Server → Agent Worker Pod → Kubernetes API → Pods/Resources
                      (K8s Cluster)     (Service Account)
```
- **Use Case**: Kubernetes-native infrastructure
- **Security**: Service accounts, RBAC, network policies
- **Performance**: Native K8s networking, optimal performance

**Agent Worker Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│              Application Server (Orchestrator)              │
│  - Ticket Processing                                         │
│  - Runbook Resolution                                        │
│  - Execution Coordination                                    │
│  - Human Approval Management                                 │
└──────────────────────┬──────────────────────────────────────┘
                        │
                        │ gRPC/HTTP API
                        │ (Authenticated, Encrypted)
                        │
        ┌───────────────┴───────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐          ┌──────────────────┐
│ Agent Worker 1   │          │ Agent Worker 2   │
│ (VPC-A)          │          │ (VPC-B)          │
│                  │          │                  │
│ - SSH Connector  │          │ - DB Connector   │
│ - API Connector  │          │ - K8s Connector  │
│ - Credential     │          │ - Credential     │
│   Client         │          │   Client         │
└──────────────────┘          └──────────────────┘
        │                                 │
        │ Direct Network Access          │
        │                                 │
        ▼                                 ▼
┌──────────────────┐          ┌──────────────────┐
│ Infrastructure   │          │ Infrastructure    │
│ (VPC-A)          │          │ (VPC-B)          │
└──────────────────┘          └──────────────────┘
```

**Agent Worker Responsibilities**:
1. **Receive Execution Commands**: From orchestrator via secure API
2. **Retrieve Credentials**: From vault (service account has vault access)
3. **Establish Connections**: To infrastructure components
4. **Execute Commands**: With proper error handling and timeout
5. **Capture Outputs**: Stdout, stderr, exit codes
6. **Report Results**: Back to orchestrator
7. **Handle Failures**: Cleanup, rollback, escalation

**Supported Connectors**:
- **SSH**: Linux/Unix servers (via asyncssh/paramiko)
- **WinRM**: Windows servers (via pywinrm)
- **Database**: MySQL, PostgreSQL, MSSQL, MongoDB, Redis
- **Cloud APIs**: AWS (boto3), Azure (Azure SDK), GCP (GCP SDK)
- **Kubernetes**: kubectl API (kubernetes Python client)
- **Container**: Docker API (docker SDK)
- **API**: REST/GraphQL endpoints (httpx/aiohttp)
- **CLI Tools**: Custom command-line tools (subprocess with proper sandboxing)

**Connection Management**:
```python
class InfrastructureConnector(ABC):
    @abstractmethod
    async def connect(self, credentials: Credentials, connection_config: dict) -> Connection:
        """Establish secure connection
        Args:
            credentials: Credentials from vault
            connection_config: {
                'host': str,
                'port': int,
                'bastion_host': Optional[str],  # For jump host pattern
                'vpn_endpoint': Optional[str],  # For VPN pattern
                'timeout': int,
                'retry_policy': dict
            }
        """
    
    @abstractmethod
    async def execute_command(self, command: str, timeout: int) -> ExecutionResult:
        """Execute command and return result"""
    
    @abstractmethod
    async def disconnect(self):
        """Close connection"""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connection is healthy"""
    
    @abstractmethod
    async def supports_connection_pattern(self, pattern: str) -> bool:
        """Check if connector supports connection pattern
        Patterns: direct, bastion, vpn, kubernetes
        """
```

**Execution Result**:
```python
class ExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    executed_at: datetime
    error_message: Optional[str]
    connection_info: dict          # Connection details (no credentials)
    agent_worker_id: str           # Which worker executed
    network_path: str              # Network path used (direct/bastion/vpn)
```

**Security**:
- Credentials never stored in code
- All credentials from vault (retrieved by worker at execution time)
- Connections encrypted (TLS/SSH)
- Connection pooling with limits
- Timeout enforcement
- Command sanitization
- Network isolation (workers in appropriate network segments)
- Worker authentication (service accounts, certificates)
- Audit logging (all connections logged)

**Network Topology Considerations**:

**1. Agent Worker Placement**:
- **Same Network Segment**: For direct access (lowest latency)
- **DMZ/Bastion Zone**: For secure access to private networks
- **Per-Environment Workers**: Separate workers for prod/staging/dev
- **Per-Region Workers**: For multi-region deployments

**2. Network Access Requirements**:
- **Outbound Connections**: Agent workers need outbound access to infrastructure
- **Inbound Connections**: Only from orchestrator (via API)
- **Firewall Rules**: Strict rules, only necessary ports
- **Network ACLs**: Additional layer of network security

**3. Credential Access Pattern**:
```
Execution Request → Agent Worker → Vault Client
                                      ↓
                                 Retrieve Credentials
                                      ↓
                                 Establish Connection
                                      ↓
                                 Execute Command
                                      ↓
                                 Invalidate Credential Cache
```

**4. Connection Lifecycle**:
- **Connection Pooling**: Reuse connections where possible (SSH, Database)
- **Connection Timeout**: Idle connections closed after timeout
- **Health Checks**: Periodic checks to ensure connection viability
- **Automatic Reconnection**: Retry logic for transient failures

---

### 3.6 Credential Vault Service

**Purpose**: Secure credential management

**Components**:
- **Vault Integration**: HashiCorp Vault / AWS Secrets Manager / Azure Key Vault
- **Credential Cache**: In-memory cache (encrypted) for performance
- **Credential Rotation**: Support for automatic rotation
- **Access Control**: RBAC for credential access

**Credential Types**:
```python
class Credential:
    id: str
    name: str
    type: str              # ssh_password, ssh_key, api_key, database, etc.
    vault_path: str        # Path in vault
    tenant_id: int
    environment: str       # prod, staging, dev
    service: str           # Service name
    last_rotated: datetime
    rotation_policy: dict
    access_policy: dict    # Who can access
```

**Access Pattern**:
```
Execution Request → Service Account → Vault Lookup → Credential Retrieval
                                                    → Decrypt → Use → Invalidate Cache
```

**Security Best Practices**:
- Credentials never logged
- Credentials never exposed in APIs
- Credentials encrypted at rest
- Credentials encrypted in transit
- Credentials rotated regularly
- Access audit logging
- Principle of least privilege

---

### 3.7 Resolution Verification Service

**Purpose**: Verify if issue is actually resolved

**Components**:
- **Postcheck Executor**: Execute runbook postchecks
- **Verification Analyzer**: Analyze postcheck outputs
- **Resolution Confirmation**: Confirm resolution with confidence score
- **Alert Suppression**: Suppress alerts if resolved

**Verification Flow**:
```
Execute Postchecks → Analyze Outputs → Resolution Check
                                           ├─ Resolved (confidence > 0.9)
                                           │   ├─ Close Ticket
                                           │   ├─ Suppress Alert
                                           │   └─ Record Success
                                           └─ Not Resolved (confidence ≤ 0.9)
                                               ├─ Escalate to Human
                                               └─ Log Failure
```

**Resolution Confidence Scoring**:
- Postcheck success: 40%
- Expected output match: 30%
- Error absence: 20%
- Performance metrics: 10%

---

### 3.8 Escalation Service

**Purpose**: Escalate to human operators when automation fails

**Escalation Triggers**:
- Runbook execution failure
- Low confidence in resolution
- Human rejection at checkpoint
- Timeout exceeded
- Critical error detected
- Manual escalation requested

**Escalation Channels**:
- **PagerDuty**: Create incident
- **ServiceNow**: Create ticket
- **Slack**: Send alert to channel
- **Email**: Send notification
- **Custom Webhook**: User-defined endpoints

**Escalation Payload**:
```python
class Escalation:
    ticket_id: str
    runbook_id: Optional[int]
    execution_session_id: int
    escalation_reason: str
    severity: str
    context: dict           # Execution logs, outputs, errors
    assigned_to: Optional[str]
    created_at: datetime
```

---

## 4. Data Models

### 4.1 Ticket Model

```python
class Ticket(Base):
    id = Column(String, primary_key=True)          # External ticket ID
    tenant_id = Column(Integer, ForeignKey(...))
    source = Column(String)                        # Monitoring tool name
    title = Column(String)
    description = Column(Text)
    severity = Column(String)                      # critical, high, medium, low
    environment = Column(String)                  # prod, staging, dev
    service = Column(String)
    status = Column(String)                        # open, analyzing, executing, resolved, escalated, closed
    analysis = Column(JSONB)                       # TicketAnalysis result
    runbook_id = Column(Integer, ForeignKey(...))
    execution_session_id = Column(Integer, ForeignKey(...))
    resolution_confirmed = Column(Boolean)
    false_positive = Column(Boolean)
    suppressed_alerts = Column(JSONB)              # List of suppressed alert IDs
    raw_payload = Column(JSONB)                    # Original ticket payload
    last_updated_event_id = Column(String)         # For real-time synchronization
    version = Column(Integer, default=1)            # Optimistic locking for updates
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    resolved_at = Column(DateTime)
    escalated_at = Column(DateTime)
```

### 4.2 Execution Session Model (Enhanced)

```python
class ExecutionSession(Base):
    # Existing fields...
    ticket_id = Column(String, ForeignKey("tickets.id"))
    validation_mode = Column(String)               # per_step, per_phase, critical_only, final_only
    human_approved = Column(Boolean, default=False)
    human_approver_id = Column(Integer, ForeignKey("users.id"))
    human_approved_at = Column(DateTime)
    auto_approved = Column(Boolean, default=False)
    escalation_reason = Column(Text)
    infrastructure_connections = Column(JSONB)    # List of connections used
    credentials_used = Column(JSONB)                # Credential IDs (audit only)
```

### 4.3 Execution Step Model (Enhanced)

```python
class ExecutionStep(Base):
    # Existing fields...
    human_approved = Column(Boolean, default=False)
    human_approver_id = Column(Integer, ForeignKey("users.id"))
    human_approved_at = Column(DateTime)
    auto_approved = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    execution_result = Column(JSONB)                # ExecutionResult object
    infrastructure_type = Column(String)            # ssh, api, database, etc.
    connection_id = Column(String)                  # Connection identifier
    rollback_executed = Column(Boolean, default=False)
    rollback_result = Column(JSONB)
```

### 4.4 Credential Model

```python
class Credential(Base):
    id = Column(String, primary_key=True)
    tenant_id = Column(Integer, ForeignKey(...))
    name = Column(String)
    type = Column(String)                          # ssh_password, ssh_key, api_key, database, etc.
    vault_path = Column(String)                     # Path in vault
    environment = Column(String)
    service = Column(String)
    last_rotated = Column(DateTime)
    rotation_policy = Column(JSONB)
    access_policy = Column(JSONB)                  # RBAC rules
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

### 4.5 Infrastructure Connection Model

```python
class InfrastructureConnection(Base):
    id = Column(String, primary_key=True)
    tenant_id = Column(Integer, ForeignKey(...))
    name = Column(String)
    type = Column(String)                          # ssh, winrm, database, api, kubernetes, etc.
    host = Column(String)
    port = Column(Integer)
    credential_id = Column(String, ForeignKey("credentials.id"))
    connection_params = Column(JSONB)               # Type-specific params
    connection_pattern = Column(String)            # direct, bastion, vpn, kubernetes
    bastion_host = Column(String, nullable=True)   # For jump host pattern
    vpn_endpoint = Column(String, nullable=True)   # For VPN pattern
    network_segment = Column(String)               # VPC, DMZ, Private, etc.
    preferred_agent_worker = Column(String, nullable=True)  # Preferred worker ID
    health_check_enabled = Column(Boolean, default=True)
    last_health_check = Column(DateTime)
    is_healthy = Column(Boolean, default=True)
    created_at = Column(DateTime)
```

### 4.6 Agent Worker Model

```python
class AgentWorker(Base):
    id = Column(String, primary_key=True)          # Worker identifier
    tenant_id = Column(Integer, ForeignKey(...))
    name = Column(String)
    status = Column(String)                        # active, inactive, maintenance, error
    network_segment = Column(String)               # VPC-A, DMZ, Private, etc.
    capabilities = Column(JSONB)                   # List of supported connector types
    current_load = Column(Integer, default=0)     # Current concurrent executions
    max_load = Column(Integer, default=10)        # Maximum concurrent executions
    last_heartbeat = Column(DateTime)
    agent_version = Column(String)
    hostname = Column(String)
    ip_address = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

---

## 5. Security Architecture

### 5.1 Authentication & Authorization Framework

**Enterprise-Grade Authentication Methods**:

#### 5.1.1 Multi-Factor Authentication (MFA)

**Primary Methods**:
1. **TOTP (Time-based One-Time Password)** - Google Authenticator, Microsoft Authenticator
2. **SMS OTP** - Secondary channel for OTP delivery
3. **Hardware Tokens** - YubiKey, RSA SecurID
4. **Push Notifications** - Mobile app-based approval
5. **Biometric Authentication** - Fingerprint, Face ID (for mobile/desktop clients)

**MFA Enforcement**:
- **Admin Users**: Always required
- **Operators**: Required for production environments
- **Viewers**: Optional, recommended
- **Service Accounts**: Certificate-based (no MFA, but stricter validation)

#### 5.1.2 Single Sign-On (SSO) Integration

**Supported Protocols**:
1. **SAML 2.0** (Primary)
   - Enterprise standard for SSO
   - Support for Azure AD, Okta, OneLogin, PingIdentity
   - SP-initiated and IdP-initiated flows
   - Signed assertions and encrypted attributes

2. **OpenID Connect (OIDC)**
   - Modern standard built on OAuth 2.0
   - Support for Google Workspace, Microsoft Azure AD, Auth0
   - JWT-based tokens with ID tokens

3. **LDAP/Active Directory**
   - Direct integration with corporate directories
   - Kerberos authentication support
   - Group-based authorization

**SSO Configuration**:
```yaml
sso:
  saml:
    enabled: true
    idp_metadata_url: "https://idp.example.com/metadata"
    sp_entity_id: "urn:troubleshooting-agent"
    acs_url: "https://agent.example.com/saml/acs"
    signing_certificate: "-----BEGIN CERTIFICATE-----..."
    encryption_certificate: "-----BEGIN CERTIFICATE-----..."
    name_id_format: "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    attribute_mapping:
      email: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
      groups: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/groups"
  
  oidc:
    enabled: true
    issuer: "https://accounts.google.com"
    client_id: "client-id"
    client_secret: "client-secret"
    redirect_uri: "https://agent.example.com/oidc/callback"
    scopes: ["openid", "profile", "email"]
```

#### 5.1.3 API Authentication

**Methods**:

1. **OAuth 2.0 with JWT Tokens** (Primary)
   - **Client Credentials Flow**: For service-to-service authentication
   - **Authorization Code Flow**: For user-facing applications
   - **Refresh Tokens**: For long-lived sessions
   - **Token Expiration**: Access tokens (15 minutes), Refresh tokens (30 days)

2. **API Keys** (Legacy/Service Accounts)
   - HMAC-SHA256 signed requests
   - Key rotation every 90 days
   - Scoped permissions per key
   - Rate limiting per key

3. **Mutual TLS (mTLS)**
   - Certificate-based authentication
   - Required for agent worker communication
   - Certificate pinning for critical connections
   - Certificate rotation automation

**API Authentication Flow**:
```
Client → Request with JWT Token
         ↓
    Validate Token Signature
         ↓
    Check Token Expiration
         ↓
    Validate Token Claims (audience, issuer)
         ↓
    Check User Permissions
         ↓
    Allow/Deny Request
```

#### 5.1.4 Agent Worker Authentication

**Certificate-Based Authentication**:
- Each agent worker has a unique X.509 certificate
- Certificate issued by internal CA
- Certificate stored in vault, not on worker filesystem
- Certificate rotation every 90 days
- Certificate revocation list (CRL) checking

**Worker Registration Flow**:
```
1. Worker generates CSR (Certificate Signing Request)
2. CSR sent to orchestrator with worker metadata
3. Orchestrator validates worker metadata
4. CA signs certificate
5. Certificate stored in vault
6. Worker retrieves certificate from vault
7. Worker registers with orchestrator using certificate
8. Orchestrator validates certificate signature
9. Worker added to registry
```

**Worker-to-Orchestrator Communication**:
- **Protocol**: gRPC over TLS 1.3
- **Authentication**: mTLS with client certificates
- **Authorization**: Certificate CN (Common Name) must match worker ID
- **Rate Limiting**: Per-worker connection limits

### 5.2 Authorization & Access Control

#### 5.2.1 Role-Based Access Control (RBAC)

**Core Roles**:

1. **Super Admin**
   - Full system access
   - User management
   - Credential management
   - System configuration
   - Audit log access

2. **Admin**
   - Tenant-level administration
   - User management within tenant
   - Credential management
   - Runbook management
   - Execution approval

3. **Operator**
   - Execute runbooks
   - Approve execution steps
   - View execution history
   - Create/edit runbooks
   - View tickets

4. **Viewer**
   - Read-only access
   - View runbooks
   - View execution history
   - View tickets
   - View analytics

5. **Service Account**
   - Limited execution permissions
   - No UI access
   - API-only access
   - Scoped to specific resources

**Permission Model**:
```python
class Permission:
    resource: str              # ticket, runbook, credential, execution, user, system
    action: str               # read, write, execute, approve, delete, manage
    scope: str                # tenant, environment, service, all
    conditions: dict          # Additional conditions (time-based, IP-based, etc.)
```

**Attribute-Based Access Control (ABAC)**:
- **Environment-based**: Users can only access their assigned environments (prod, staging, dev)
- **Service-based**: Users restricted to specific services
- **Time-based**: Access restrictions by time of day
- **IP-based**: Access restrictions by IP address/range
- **Device-based**: Require registered devices

#### 5.2.2 Least Privilege Principle

**Implementation**:
- Users granted minimum permissions needed
- Just-in-time (JIT) access for elevated permissions
- Temporary permission elevation with approval
- Automatic permission revocation after use
- Regular access reviews (quarterly)

**Permission Elevation**:
```
User requests elevated permission
    ↓
Requires approval from admin
    ↓
Permission granted temporarily (1-4 hours)
    ↓
All actions logged with elevated permission flag
    ↓
Automatic revocation after timeout
```

### 5.3 Credential Security

#### 5.3.1 Credential Storage

**Vault Integration**:
- **Primary**: HashiCorp Vault (recommended)
- **Alternatives**: AWS Secrets Manager, Azure Key Vault, Google Secret Manager
- **Backup**: Encrypted database storage (fallback only)

**Vault Authentication Methods**:
1. **AppRole Authentication** (Primary)
   - Service accounts use AppRole
   - Role-based access policies
   - Secret ID rotation

2. **AWS IAM Authentication**
   - For AWS-hosted infrastructure
   - IAM role-based access

3. **Azure AD Authentication**
   - For Azure-hosted infrastructure
   - Service principal-based

4. **Kubernetes Service Account**
   - For K8s deployments
   - Token-based authentication

**Credential Lifecycle**:
```
1. Credential Creation
   ↓
2. Encrypt and Store in Vault
   ↓
3. Access via Service Account
   ↓
4. Use Credential (Temporary)
   ↓
5. Invalidate from Cache
   ↓
6. Rotate Credential (Scheduled)
   ↓
7. Update in Vault
   ↓
8. Verify New Credential
   ↓
9. Archive Old Credential
```

#### 5.3.2 Credential Access Controls

**Access Policies**:
- **Time-based**: Credentials accessible only during business hours
- **IP-based**: Access restricted to specific IP ranges
- **Usage-based**: Limit number of credential retrievals
- **Environment-based**: Production credentials restricted to production workers

**Credential Rotation**:
- **Automatic Rotation**: Scheduled rotation (30, 60, 90 days)
- **Event-based Rotation**: Rotate on security incident
- **Manual Rotation**: On-demand rotation with approval
- **Zero-downtime Rotation**: Gradual rotation with overlap period

**Credential Auditing**:
- All credential access logged
- Credential values never logged
- Access patterns analyzed for anomalies
- Alerts on suspicious access patterns

### 5.4 Network Security

#### 5.4.1 Network Segmentation

**Network Zones**:
1. **DMZ (Demilitarized Zone)**
   - Public-facing services
   - Webhook receivers
   - Strict firewall rules
   - No direct database access

2. **Application Zone**
   - Application servers
   - Database access
   - Vault access
   - No direct internet access

3. **Agent Worker Zone**
   - Agent workers
   - Infrastructure access
   - Vault access
   - Network isolation per environment

4. **Database Zone**
   - Database servers
   - Replication only
   - No application access (via API only)

**Network Access Controls**:
- **Firewall Rules**: Strict ingress/egress rules
- **Network ACLs**: Additional layer of network filtering
- **VPC Security Groups**: Cloud-specific network isolation
- **Network Policies**: Kubernetes network policies for containerized deployments

#### 5.4.2 Encryption

**Encryption in Transit**:
- **TLS 1.3**: All HTTPS connections
- **SSH**: All SSH connections (key-based, no passwords)
- **Database**: TLS required for all database connections
- **gRPC**: TLS for all gRPC connections
- **Message Queue**: TLS for RabbitMQ/Kafka

**Encryption at Rest**:
- **Database**: Transparent Data Encryption (TDE)
- **Vault**: Vault's built-in encryption
- **File Storage**: Encrypted volumes (LUKS, AWS EBS encryption)
- **Backups**: Encrypted backups with separate keys

**Key Management**:
- **Key Rotation**: Automatic key rotation every 90 days
- **Key Storage**: Keys stored in hardware security module (HSM) or cloud KMS
- **Key Separation**: Different keys for different environments
- **Key Escrow**: Emergency key recovery procedures

### 5.5 Application Security

#### 5.5.1 Input Validation & Sanitization

**Command Injection Prevention**:
- **Parameterized Commands**: All commands use parameterized inputs
- **Whitelist Validation**: Only allow whitelisted commands
- **Command Sanitization**: Remove/escape special characters
- **Output Encoding**: Encode all outputs before display

**SQL Injection Prevention**:
- **Parameterized Queries**: All database queries use parameters
- **ORM Usage**: Use ORM (SQLAlchemy) to prevent raw SQL
- **Input Validation**: Validate all inputs before processing

**XSS Prevention**:
- **Output Encoding**: Encode all user-generated content
- **Content Security Policy (CSP)**: Restrict allowed sources
- **HTTPOnly Cookies**: Prevent JavaScript access to cookies

#### 5.5.2 Session Management

**Session Configuration**:
- **Session Timeout**: 30 minutes inactivity
- **Session Fixation**: Regenerate session ID on login
- **Secure Cookies**: HTTPS-only, Secure flag
- **SameSite Cookies**: Prevent CSRF attacks
- **Session Storage**: Server-side storage (Redis with encryption)

**Session Security**:
```python
session_config = {
    "timeout": 1800,  # 30 minutes
    "regenerate_on_login": True,
    "secure": True,  # HTTPS only
    "httponly": True,  # No JavaScript access
    "samesite": "Strict",  # CSRF protection
    "storage": "redis",  # Server-side storage
    "encryption": True  # Encrypt session data
}
```

#### 5.5.3 API Security

**Rate Limiting**:
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Per API Key**: 10000 requests/hour
- **Burst Protection**: Maximum 100 requests/minute

**Request Validation**:
- **Schema Validation**: Validate all request schemas
- **Size Limits**: Maximum request size (10MB)
- **Content-Type Validation**: Strict content-type checking
- **Parameter Validation**: Validate all parameters

**API Security Headers**:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### 5.6 Audit & Compliance

#### 5.6.1 Comprehensive Audit Logging

**Audited Events**:
- **Authentication Events**: Login, logout, MFA attempts, SSO flows
- **Authorization Events**: Permission grants, denials, elevation requests
- **Credential Events**: Access, rotation, creation, deletion
- **Execution Events**: Command execution, approvals, rejections
- **Configuration Events**: System configuration changes
- **Data Access Events**: Runbook access, ticket access, credential access

**Audit Log Schema**:
```python
class AuditLog(Base):
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer)
    user_id = Column(Integer)
    service_account_id = Column(String)  # If service account
    action = Column(String)              # login, execute_command, approve_step, etc.
    resource_type = Column(String)       # ticket, runbook, credential, execution
    resource_id = Column(String)
    details = Column(JSONB)              # Action-specific details
    ip_address = Column(String)
    user_agent = Column(String)
    session_id = Column(String)
    mfa_method = Column(String)          # If MFA was used
    result = Column(String)              # success, failure, denied
    risk_score = Column(Integer)         # Calculated risk score
    created_at = Column(DateTime)
    log_hash = Column(String)            # Hash of log entry for integrity
    previous_hash = Column(String)       # Hash chain for non-repudiation
```

**Audit Log Immutability & Distribution**:

**WORM Storage (Write-Once-Read-Many)**:
```python
# Audit logs stored in WORM-compliant storage
class ImmutableAuditLog:
    def __init__(self):
        # Primary storage: S3 Object Lock (Governance mode)
        self.s3_client = boto3.client('s3')
        self.bucket = "audit-logs-immutable"
        # Retention: 7 years (compliance requirement)
        self.retention_period = 2555  # days
    
    def write_log(self, log_entry: dict):
        """Write log entry with immutability guarantees"""
        # Generate log entry hash
        log_hash = hashlib.sha256(json.dumps(log_entry, sort_keys=True).encode()).hexdigest()
        log_entry['log_hash'] = log_hash
        
        # Get previous log hash for chain
        previous_hash = self.get_latest_log_hash()
        log_entry['previous_hash'] = previous_hash
        
        # Calculate chain hash
        chain_hash = hashlib.sha256(
            f"{previous_hash}{log_hash}".encode()
        ).hexdigest()
        log_entry['chain_hash'] = chain_hash
        
        # Write to S3 with Object Lock
        key = f"logs/{log_entry['tenant_id']}/{log_entry['created_at']}/{log_hash}.json"
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(log_entry),
            ObjectLockMode='GOVERNANCE',
            ObjectLockRetainUntilDate=datetime.now() + timedelta(days=self.retention_period),
            Metadata={
                'log-hash': log_hash,
                'chain-hash': chain_hash,
                'previous-hash': previous_hash
            }
        )
        
        # Forward to SIEM
        self.forward_to_siem(log_entry)
```

**SIEM Forwarding with Integrity Attestations**:
```python
class SIEMForwarder:
    def __init__(self):
        self.siem_endpoint = os.getenv('SIEM_ENDPOINT')
        self.siem_api_key = get_secret('siem_api_key')
    
    def forward_to_siem(self, log_entry: dict):
        """Forward log entry to SIEM with integrity attestation"""
        # Sign log entry
        signature = self.sign_log_entry(log_entry)
        
        payload = {
            'log_entry': log_entry,
            'signature': signature,
            'attestation': {
                'timestamp': time.time(),
                'source': 'troubleshooting-agent',
                'version': '1.0.0',
                'chain_hash': log_entry['chain_hash']
            }
        }
        
        # Forward to SIEM (Splunk, ELK, QRadar, etc.)
        response = requests.post(
            self.siem_endpoint,
            json=payload,
            headers={
                'Authorization': f'Bearer {self.siem_api_key}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        response.raise_for_status()
```

**Log Hash Chaining for Non-Repudiation**:
```python
class LogHashChain:
    def __init__(self):
        self.chain = []
    
    def add_log_entry(self, log_entry: dict):
        """Add log entry to hash chain"""
        # Calculate hash of current entry
        entry_hash = hashlib.sha256(
            json.dumps(log_entry, sort_keys=True).encode()
        ).hexdigest()
        
        # Get previous hash
        previous_hash = self.get_latest_hash() if self.chain else "0" * 64
        
        # Calculate chain hash
        chain_hash = hashlib.sha256(
            f"{previous_hash}{entry_hash}".encode()
        ).hexdigest()
        
        # Store in chain
        chain_entry = {
            'entry_hash': entry_hash,
            'previous_hash': previous_hash,
            'chain_hash': chain_hash,
            'timestamp': time.time(),
            'log_entry': log_entry
        }
        self.chain.append(chain_entry)
        
        return chain_entry
    
    def verify_chain(self) -> bool:
        """Verify integrity of hash chain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Verify chain hash
            expected_chain_hash = hashlib.sha256(
                f"{previous['chain_hash']}{current['entry_hash']}".encode()
            ).hexdigest()
            
            if current['chain_hash'] != expected_chain_hash:
                return False
        
        return True
```

**Clock Synchronization**:
```python
# NTP synchronization for accurate timestamps
class TimeSync:
    def __init__(self):
        self.ntp_client = ntplib.NTPClient()
        self.ntp_servers = [
            'pool.ntp.org',
            'time.google.com',
            'time.cloudflare.com'
        ]
    
    def get_synchronized_time(self) -> datetime:
        """Get synchronized time from NTP"""
        for server in self.ntp_servers:
            try:
                response = self.ntp_client.request(server, version=3)
                synchronized_time = datetime.fromtimestamp(response.tx_time)
                # Verify clock skew is acceptable (< 1 second)
                local_time = datetime.now()
                skew = abs((synchronized_time - local_time).total_seconds())
                if skew < 1.0:
                    return synchronized_time
            except Exception:
                continue
        
        # Fallback to local time if NTP fails
        return datetime.now()
    
    def log_with_sync_time(self, log_entry: dict):
        """Add synchronized timestamp to log entry"""
        log_entry['timestamp'] = self.get_synchronized_time().isoformat()
        log_entry['timestamp_source'] = 'ntp'
        log_entry['clock_skew'] = self.get_clock_skew()
        return log_entry
```

**Log Signing**:
```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

class LogSigner:
    def __init__(self):
        # Load signing key from vault
        self.private_key = self.load_signing_key()
        self.public_key = self.private_key.public_key()
    
    def sign_log_entry(self, log_entry: dict) -> str:
        """Sign log entry with RSA private key"""
        # Serialize log entry
        log_json = json.dumps(log_entry, sort_keys=True)
        
        # Sign with RSA-PSS
        signature = self.private_key.sign(
            log_json.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Return base64-encoded signature
        return base64.b64encode(signature).decode()
    
    def verify_signature(self, log_entry: dict, signature: str) -> bool:
        """Verify log entry signature"""
        try:
            log_json = json.dumps(log_entry, sort_keys=True)
            sig_bytes = base64.b64decode(signature)
            
            self.public_key.verify(
                sig_bytes,
                log_json.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
```

**Audit Log Retention**:
- **Authentication Logs**: 1 year
- **Execution Logs**: 2 years
- **Credential Access Logs**: 3 years
- **Compliance Logs**: 7 years (for regulatory requirements)
- **WORM Storage**: All logs stored in write-once storage for compliance
- **SIEM Retention**: Forwarded logs retained per SIEM policy

#### 5.6.2 Security Monitoring

**Real-time Monitoring**:
- **Anomaly Detection**: ML-based anomaly detection
- **Failed Login Alerts**: Alert after 3 failed attempts
- **Privilege Escalation Alerts**: Alert on permission elevation
- **Unusual Access Patterns**: Alert on access from new locations/devices
- **Credential Access Alerts**: Alert on credential access outside business hours

**Security Metrics**:
- Failed authentication attempts
- Privilege escalation requests
- Credential access frequency
- API rate limit violations
- Suspicious command executions

#### 5.6.3 Compliance

**SOC 2 Type II**:
- Security controls documentation
- Regular security assessments
- Incident response procedures
- Access control reviews

**GDPR Compliance**:
- Data retention policies
- Right to erasure
- Data portability
- Privacy by design

**HIPAA Compliance** (if applicable):
- PHI encryption
- Access controls
- Audit trails
- Business associate agreements

**PCI-DSS Compliance** (if handling payment data):
- Network segmentation
- Encryption requirements
- Access controls
- Regular security testing

### 5.7 Security Incident Response

#### 5.7.1 Incident Detection

**Automated Detection**:
- Intrusion detection system (IDS)
- Security information and event management (SIEM)
- Anomaly detection algorithms
- Threat intelligence feeds

**Incident Types**:
- Unauthorized access attempts
- Credential compromise
- Malicious command execution
- Data exfiltration attempts
- Denial of service attacks

#### 5.7.2 Incident Response Procedures

**Response Steps**:
1. **Detection**: Automated or manual detection
2. **Containment**: Isolate affected systems
3. **Investigation**: Analyze incident details
4. **Eradication**: Remove threat
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Document and improve

**Incident Response Team**:
- Security team lead
- System administrators
- Network administrators
- Legal/compliance team
- Executive sponsor

### 5.9 Critical Security Enhancements

This section addresses critical gaps identified in security reviews and ensures enterprise-grade security standards.

#### 5.9.1 Database-Level Tenant Isolation (CRITICAL)

**Row-Level Security (RLS) Implementation**:

**Requirement**: All tenant-scoped tables MUST have RLS policies enabled to prevent cross-tenant data leakage, even if application code has bugs.

**Implementation**:
```sql
-- Enable RLS with FORCE (deny-by-default)
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets FORCE ROW LEVEL SECURITY;  -- Prevents bypass even for table owners
ALTER TABLE runbooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE runbooks FORCE ROW LEVEL SECURITY;
ALTER TABLE execution_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE credentials FORCE ROW LEVEL SECURITY;
ALTER TABLE infrastructure_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE infrastructure_connections FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

-- Create policies for each table (deny-by-default)
CREATE POLICY tenant_isolation_tickets ON tickets
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::INTEGER);

CREATE POLICY tenant_isolation_runbooks ON runbooks
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::INTEGER);

-- Similar policies for all tenant-scoped tables

-- CRITICAL: If app.current_tenant_id is not set, ALL access is blocked
-- This is enforced by PostgreSQL's RLS deny-by-default behavior
```

**Deny-by-Default Behavior**:
- **If `app.current_tenant_id` is NOT set**: ALL queries return zero rows (access denied)
- **If `app.current_tenant_id` is set incorrectly**: Only matching tenant's data is accessible
- **FORCE ROW LEVEL SECURITY**: Prevents even table owners from bypassing RLS
- **Cannot be disabled**: RLS policies are enforced at database level, not application level

**Per-Session Tenant Context**:
```python
# Application layer sets tenant context at connection start
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def set_tenant_context_on_connect(dbapi_conn, connection_record):
    """Set tenant context when connection is established"""
    tenant_id = get_current_tenant_id()  # From authenticated user/session
    if not tenant_id:
        raise SecurityError("Tenant ID must be set before database access")
    dbapi_conn.execute(f"SET LOCAL app.current_tenant_id = {tenant_id}")

@event.listens_for(Engine, "begin")
def set_tenant_context_on_transaction(dbapi_conn):
    """Ensure tenant context is set at transaction start"""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise SecurityError("Tenant ID must be set before transaction")
    dbapi_conn.execute(f"SET LOCAL app.current_tenant_id = {tenant_id}")

# Connection pool hook test (CI/CD)
def test_tenant_context_always_set():
    """Verify tenant context is set on every transaction"""
    with db_session() as session:
        # Test that tenant_id is always set
        result = session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        tenant_id = result.scalar()
        assert tenant_id is not None, "Tenant ID must be set on all connections"
        assert tenant_id.isdigit(), "Tenant ID must be numeric"
    
    # Test deny-by-default behavior
    with db_session() as session:
        # Try to access without tenant context
        session.execute(text("SET LOCAL app.current_tenant_id = NULL"))
        result = session.execute(text("SELECT COUNT(*) FROM tickets"))
        count = result.scalar()
        assert count == 0, "RLS should block all access when tenant_id is not set"
```

**Connection Pool Configuration**:
```python
# Ensure tenant context is set before any query
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://...",
    poolclass=QueuePool,
    pool_pre_ping=True,  # Verify connection before use
    connect_args={
        "options": "-c app.current_tenant_id=0"  # Default to 0 (invalid), must be overridden
    }
)

# Middleware to set tenant context per request
@app.middleware("http")
async def set_tenant_context(request: Request, call_next):
    tenant_id = get_tenant_from_request(request)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID required")
    
    # Set tenant context for this request
    with tenant_context(tenant_id):
        response = await call_next(request)
    return response
```

**Tenant Context Verification**:
- Connection pool hook verifies tenant_id is set on every transaction
- CI/CD test runs as part of test suite (blocking)
- Application-level check before any database operation
- Database-level enforcement via RLS policies

#### 5.9.2 Break-Glass & Emergency Access (CRITICAL)

**Break-Glass Access Flow**:

**Requirements**:
- Time-boxed emergency access (maximum 4 hours)
- Dual-approval required (two admins must approve)
- Enhanced logging and monitoring
- Mandatory post-incident review

**Implementation**:
```python
class BreakGlassRequest(Base):
    id = Column(Integer, primary_key=True)
    requested_by = Column(Integer, ForeignKey("users.id"))
    approver_1 = Column(Integer, ForeignKey("users.id"), nullable=True)
    approver_2 = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=False)
    requested_permissions = Column(JSONB)  # What permissions needed
    approved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime)
    revoked_at = Column(DateTime, nullable=True)
    post_incident_review_id = Column(Integer, ForeignKey("incident_reviews.id"), nullable=True)
    created_at = Column(DateTime)
```

**Break-Glass Flow**:
```
1. User requests break-glass access
   ↓
2. System alerts two designated admins
   ↓
3. Admin 1 approves (with reason)
   ↓
4. Admin 2 approves (with reason)
   ↓
5. Access granted (time-boxed, max 4 hours)
   ↓
6. All actions logged with break-glass flag
   ↓
7. Automatic revocation after timeout
   ↓
8. Mandatory post-incident review within 24 hours
```

**Enhanced Logging**:
- All break-glass actions logged with `break_glass: true` flag
- Real-time alerts to security team
- Immutable audit trail
- Cannot be deleted or modified

**Post-Incident Review**:
- Must be completed within 24 hours
- Review what was accessed and why
- Document lessons learned
- Update policies if needed

#### 5.9.3 Service Account Taxonomy & Governance (CRITICAL)

**Service Account Classification**:

**Categories**:
1. **System Service Accounts**
   - Orchestrator service account
   - Database service account
   - Vault service account
   - Highest privileges, minimal scope

2. **Agent Worker Service Accounts**
   - One per worker or per environment
   - Scoped to specific network segments
   - Limited to execution permissions

3. **Integration Service Accounts**
   - Ticketing tool integration
   - Monitoring tool integration
   - Read-only or write-only scopes

4. **Application Service Accounts**
   - Background job processors
   - Scheduled tasks
   - Scoped to specific operations

**Policy-as-Code Enforcement**:

**Using OPA (Open Policy Agent) / Gatekeeper**:
```rego
# service_account_policy.rego
package service_accounts

# Service account must have defined scope
default allow = false

allow {
    input.service_account.type == "agent_worker"
    input.service_account.scope == "execution"
    input.service_account.network_segment != ""
    input.service_account.max_lifetime_hours <= 720  # 30 days
}

allow {
    input.service_account.type == "integration"
    input.service_account.scope == "read_only"
    input.service_account.integration_name != ""
}

# Runbook step category policies
package runbook_steps

# Stop/reboot commands require admin approval
deny[msg] {
    input.step.command =~ ".*(stop|reboot|shutdown|halt).*"
    input.step.approver_role != "admin"
    msg := "Stop/reboot commands require admin approval"
}

# Destructive database operations require admin approval
deny[msg] {
    input.step.command =~ ".*(DROP|TRUNCATE|DELETE FROM).*"
    input.step.approver_role != "admin"
    msg := "Destructive database operations require admin approval"
}

# Production credentials only accessible from production workers
package credential_access

deny[msg] {
    input.credential.environment == "production"
    input.worker.environment != "production"
    msg := "Production credentials can only be accessed from production workers"
}

# Credential scope validation
deny[msg] {
    input.credential.scope != input.worker.scope
    msg := sprintf("Credential scope %v does not match worker scope %v", 
                   [input.credential.scope, input.worker.scope])
}

# Network egress policies
package network_egress

# Deny internet egress from workers by default
default allow_egress = false

# Allow specific outbound connections
allow_egress {
    input.destination.type == "vault"
    input.destination.host == "vault.internal"
}

allow_egress {
    input.destination.type == "database"
    input.destination.host =~ ".*\\.internal$"
}

allow_egress {
    input.destination.type == "orchestrator"
    input.destination.host == "orchestrator.internal"
}

# Deny all other egress
deny[msg] {
    not allow_egress
    msg := sprintf("Egress to %v:%v not allowed", 
                   [input.destination.host, input.destination.port])
}
```

**Extended OPA Policies**:

**Runbook Step Categories**:
```rego
# runbook_step_policies.rego
package runbook_steps

# Critical commands requiring admin approval
critical_commands = [
    "stop", "reboot", "shutdown", "halt",
    "DROP", "TRUNCATE", "DELETE FROM",
    "rm -rf", "mkfs", "dd if="
]

deny[msg] {
    some cmd in critical_commands
    contains(input.step.command, cmd)
    input.step.approver_role != "admin"
    msg := sprintf("Command '%v' requires admin approval", [cmd])
}

# Environment-specific restrictions
deny[msg] {
    input.step.environment == "production"
    contains(input.step.command, "DROP DATABASE")
    msg := "DROP DATABASE not allowed in production"
}
```

**Credential Scope Policies**:
```rego
# credential_scope_policies.rego
package credential_scopes

# Production credentials only from production workers
deny[msg] {
    input.credential.environment == "production"
    input.worker.environment != "production"
    msg := "Production credentials can only be accessed from production workers"
}

# Staging credentials only from staging workers
deny[msg] {
    input.credential.environment == "staging"
    input.worker.environment != "staging"
    msg := "Staging credentials can only be accessed from staging workers"
}

# Credential scope must match worker capabilities
deny[msg] {
    input.credential.type == "database"
    "database" not in input.worker.capabilities
    msg := "Worker does not have database capability"
}
```

**Network Egress Policies**:
```rego
# network_egress_policies.rego
package network_egress

# Default deny internet egress
default allow_internet = false

# Allow specific internal services
allow_internet {
    input.destination.type == "vault"
    input.destination.host =~ ".*\\.internal$|.*\\.local$"
}

allow_internet {
    input.destination.type == "orchestrator"
    input.destination.host == "orchestrator.internal"
}

allow_internet {
    input.destination.type == "database"
    input.destination.host =~ ".*\\.internal$"
}

# Deny all internet egress
deny[msg] {
    not allow_internet
    input.destination.type == "internet"
    msg := "Internet egress not allowed from workers"
}

# Allow specific external APIs (if needed)
allow_internet {
    input.destination.type == "api"
    input.destination.host in [
        "api.servicenow.com",
        "api.atlassian.com"
    ]
    input.destination.port == 443
}
```

**Enforcement Points**:
- Service account creation
- Permission grants
- Credential access
- API requests
- Runbook step execution
- Network egress attempts

**Service Account Lifecycle**:
- Automatic expiration (default: 90 days)
- Rotation required before expiration
- Deprovisioning on inactivity (30 days)
- Regular review (quarterly)

#### 5.9.4 Credential Bootstrap ("Secret Zero") (CRITICAL)

**Worker-to-Vault Authentication**:

**AppRole with Short-Lived SecretIDs**:
```python
# Worker bootstrap process
1. Worker starts with minimal bootstrap credentials
2. Worker requests Vault AppRole auth using RoleID
3. Vault validates and issues short-lived SecretID (1 hour)
4. Worker uses SecretID to get Vault token (TTL: 4 hours)
5. Worker retrieves actual credentials from vault
6. Worker caches credentials in memory (encrypted)
7. SecretID expires, cannot be reused
```

**Ephemeral Credentials**:
- **Dynamic Database Credentials**: Vault generates temporary DB credentials (TTL: 1 hour)
- **SSH Certificates**: Vault issues short-lived SSH certificates (validity: 1 hour)
- **AWS STS Tokens**: Temporary AWS credentials (TTL: 1 hour)
- **No long-lived credentials**: All credentials are ephemeral

**Cloud IAM Authentication** (Alternative):
```python
# AWS IAM Authentication to Vault
1. Worker runs on EC2 with IAM role
2. Worker requests Vault auth using AWS IAM method
3. Vault validates IAM role signature
4. Vault issues token scoped to worker's role
5. Worker uses token to access secrets
```

**Bootstrap Credential Storage**:
- Bootstrap credentials stored in:
  - Cloud KMS (AWS KMS, Azure Key Vault)
  - Kubernetes secrets (for K8s deployments)
  - Not in code or config files
- Bootstrap credentials rotated every 30 days
- Only used for initial Vault authentication

#### 5.9.5 Worker Secret Handling (CRITICAL)

**No Secrets on Disk**:
- Credentials NEVER written to filesystem
- All credentials stored in memory only
- Memory cleared on process exit
- Memory encryption in use

**Memory Protection**:
```python
import mlock
import ctypes

class SecureCredentialHandler:
    def __init__(self):
        self._credentials = {}  # In-memory only
        # Lock memory to prevent swapping
        mlock.mlockall(mlock.MCL_CURRENT | mlock.MCL_FUTURE)
        # Disable swap for this process
        libc = ctypes.CDLL("libc.so.6")
        libc.madvise.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
        libc.madvise.restype = ctypes.c_int
        # MADV_NOSWAP = 7
        libc.madvise(self._credentials, sys.getsizeof(self._credentials), 7)
    
    def get_credential(self, credential_id: str) -> Credential:
        # Retrieve from vault
        cred = vault.get_secret(credential_id)
        # Store in memory (encrypted) with short TTL
        self._credentials[credential_id] = {
            'value': encrypt(cred),
            'expires_at': time.time() + 300,  # 5 minute TTL
            'last_used': time.time()
        }
        return cred
    
    def clear_credential(self, credential_id: str):
        # Secure wipe: Overwrite memory before deletion
        if credential_id in self._credentials:
            cred_data = self._credentials[credential_id]
            # Overwrite with random data
            secure_wipe(cred_data['value'])
            # Overwrite with zeros
            cred_data['value'] = b'\x00' * len(cred_data['value'])
            del self._credentials[credential_id]
    
    def secure_wipe_per_step(self):
        """Clear credentials after each execution step"""
        for cred_id in list(self._credentials.keys()):
            cred_data = self._credentials[cred_id]
            # Clear if expired or unused for 1 minute
            if time.time() > cred_data['expires_at'] or \
               (time.time() - cred_data['last_used']) > 60:
                self.clear_credential(cred_id)
```

**Separate Minimal Helper Process**:
```python
# Minimal credential retrieval process (separate from executor)
# Runs with minimal privileges, only handles vault communication
class CredentialRetrievalProcess:
    def __init__(self):
        self.vault_client = VaultClient()
        # Process runs with minimal capabilities
        # Only NET_BIND_SERVICE capability
        # No file system write access
        # No network egress except to vault
    
    def retrieve_credential(self, credential_id: str) -> EncryptedCredential:
        """Retrieve credential from vault and return encrypted"""
        credential = self.vault_client.get_secret(credential_id)
        # Encrypt before returning to executor process
        return encrypt(credential)
    
    def run(self):
        """Run as separate process, communicate via secure IPC"""
        # Listen on Unix domain socket
        # Only accepts connections from executor process
        # Returns encrypted credentials only
```

**Output Redaction**:
```python
# Worker output sanitization
class OutputSanitizer:
    SENSITIVE_PATTERNS = [
        r'password["\s]*[:=]["\s]*([^"\s]+)',
        r'api[_-]?key["\s]*[:=]["\s]*([^"\s]+)',
        r'token["\s]*[:=]["\s]*([^"\s]+)',
        r'secret["\s]*[:=]["\s]*([^"\s]+)',
        r'credential["\s]*[:=]["\s]*([^"\s]+)',
        # Add more patterns
    ]
    
    def sanitize(self, output: str) -> str:
        for pattern in self.SENSITIVE_PATTERNS:
            output = re.sub(pattern, r'\1', '[REDACTED]', output)
        return output
```

**Memory Scrubbing**:
- Credentials cleared from memory after use
- Sensitive data overwritten with zeros
- Memory protection: mlock() to prevent swapping
- Process isolation: Separate process for credential handling
- Per-step secure wipe: Credentials cleared after each execution step
- Short TTL: Credentials expire after 5 minutes in cache

**Logging Prevention**:
- Secrets never logged (even in debug mode)
- Log redaction for command outputs
- **CI/CD test: "forbid secrets in logs" check (BLOCKING)**
- Pre-commit hooks check for credential patterns

**Blocking CI/CD Test**:
```python
# tests/test_secrets_in_logs.py
def test_forbid_secrets_in_logs():
    """BLOCKING TEST: Fail if secrets found in logs"""
    log_files = find_all_log_files()
    secrets_found = []
    
    for log_file in log_files:
        content = read_file(log_file)
        # Check for credential patterns
        for pattern in SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                secrets_found.append({
                    'file': log_file,
                    'pattern': pattern,
                    'matches': matches
                })
    
    assert len(secrets_found) == 0, \
        f"Secrets found in logs: {secrets_found}. This is a blocking issue."
    
    # Test that redaction actually works
    test_output = "password=secret123"
    sanitized = OutputSanitizer().sanitize(test_output)
    assert "secret123" not in sanitized
    assert "[REDACTED]" in sanitized
```

**Implementation**:
```python
# Worker credential handling
class SecureCredentialHandler:
    def __init__(self):
        self._credentials = {}  # In-memory only
        # Lock memory to prevent swapping
        mlock.mlockall(mlock.MCL_CURRENT | mlock.MCL_FUTURE)
    
    def get_credential(self, credential_id: str) -> Credential:
        # Use separate helper process for retrieval
        helper = CredentialRetrievalProcess()
        encrypted_cred = helper.retrieve_credential(credential_id)
        
        # Decrypt and store in memory (with TTL)
        cred = decrypt(encrypted_cred)
        self._credentials[credential_id] = {
            'value': cred,
            'expires_at': time.time() + 300,  # 5 minute TTL
            'last_used': time.time()
        }
        return cred
    
    def clear_credential(self, credential_id: str):
        # Overwrite memory before deletion
        if credential_id in self._credentials:
            cred = self._credentials[credential_id]
            secure_delete(cred['value'])  # Overwrite with zeros
            del self._credentials[credential_id]
    
    def secure_wipe_per_step(self):
        """Clear credentials after each execution step"""
        for cred_id in list(self._credentials.keys()):
            self.clear_credential(cred_id)
    
    def __del__(self):
        # Clear all credentials on destruction
        for cred_id in list(self._credentials.keys()):
            self.clear_credential(cred_id)
```

#### 5.9.6 Command Execution Guardrails (CRITICAL)

**Allow-List/Deny-List Command Policy**:

```yaml
# command_policy.yaml
command_policies:
  - service: postgresql
    environment: production
    allowed_commands:
      - "SELECT * FROM"
      - "VACUUM"
      - "REINDEX"
    denied_commands:
      - "DROP DATABASE"
      - "DROP TABLE"
      - "TRUNCATE"
      - "DELETE FROM"
    requires_approval:
      - "ALTER TABLE"
      - "CREATE INDEX"
  
  - service: linux_server
    environment: production
    allowed_commands:
      - "systemctl status"
      - "systemctl restart"
      - "df -h"
    denied_commands:
      - "rm -rf /"
      - "dd if="
      - "mkfs"
    requires_approval:
      - "systemctl stop"
      - "reboot"
```

**Dry-Run/Simulation Mode**:
```python
class CommandExecutor:
    def execute(self, command: str, dry_run: bool = False):
        if dry_run:
            # Validate command syntax
            # Check against allow/deny lists
            # Show what would be executed
            # Return simulated output
            return self.simulate(command)
        else:
            return self.execute_real(command)
```

**Blast-Radius Estimator**:
```python
class BlastRadiusEstimator:
    def estimate(self, command: str, runbook: Runbook) -> dict:
        affected_hosts = self.count_affected_hosts(runbook)
        data_touching = self.detect_data_operations(command)
        destructive_ops = self.detect_destructive_operations(command)
        
        risk_score = (
            affected_hosts * 10 +
            data_touching * 20 +
            destructive_ops * 30
        )
        
        approval_level = "auto" if risk_score < 50 else "operator" if risk_score < 100 else "admin"
        
        return {
            "risk_score": risk_score,
            "affected_hosts": affected_hosts,
            "requires_approval_level": approval_level,
            "blast_radius": "low" if risk_score < 50 else "medium" if risk_score < 100 else "high"
        }
```

**Output Validators**:
```yaml
# runbook_step.yaml
steps:
  - name: check_database_status
    command: "SELECT status FROM pg_stat_database WHERE datname = '{{database_name}}'"
    expected_output:
      type: json
      schema:
        type: object
        properties:
          status:
            type: string
            enum: ["active", "idle"]
      validator: regex
      pattern: "^status: (active|idle)$"
    on_validation_failure: escalate
```

#### 5.9.7 Sandboxing & Isolation (CRITICAL)

**Sandbox Implementation**:

**Linux Security Modules**:
- **seccomp**: System call filtering
- **AppArmor**: Application-specific access control
- **SELinux**: Mandatory access control

**Container Sandboxing**:
```yaml
# Docker/Kubernetes security context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE  # Only if needed
  seccompProfile:
    type: RuntimeDefault
  appArmorProfile: runtime/default
  selinuxOptions:
    type: container_t
```

**Minimal Container Images**:
- Distroless or scratch base images
- No shell, no package manager
- Only required binaries
- Read-only root filesystem

**Network Isolation**:
- Worker containers in isolated network namespace
- No direct internet access
- Only allowed outbound connections
- Network policies enforced

**Resource Limits**:
```yaml
resources:
  limits:
    cpu: "500m"
    memory: "512Mi"
  requests:
    cpu: "100m"
    memory: "128Mi"
```

#### 5.9.8 Supply Chain Security (CRITICAL)

**Container Image Integrity**:

**Signed Images with Cosign**:
```bash
# Build and sign image
docker build -t troubleshooting-agent:1.0.0 .
cosign sign --key cosign.key troubleshooting-agent:1.0.0

# Verify signature before deployment
cosign verify --key cosign.pub troubleshooting-agent:1.0.0
```

**SBOM (Software Bill of Materials)**:
- Generate SBOM for all images
- Track all dependencies
- Vulnerability scanning against SBOM
- SBOM attached to image as attestation

**SLSA Attestations**:
- Provenance attestations (where image came from)
- Build attestations (how image was built)
- Dependency attestations (what dependencies used)

**OPA/Gatekeeper Admission**:
```rego
# image_policy.rego
package image_policy

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not startswith(container.image, "troubleshooting-agent-registry/")
    msg := "Image must be from approved registry"
}

deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not has_valid_signature(container.image)
    msg := "Image must be signed"
}
```

**Agent Binary Code Signing**:
- Sign agent binaries with code signing certificate
- Verify signature at worker startup
- Pin CA certificate for signature verification
- Reject unsigned or invalid signatures

**Remote Attestation**:
- TPM-based attestation for critical workers
- Verify worker integrity before execution
- Attestation checks for production environments

#### 5.9.9 Webhook Security & Idempotency (CRITICAL)

**Replay Protection**:

**Nonce + Timestamp Validation**:
```python
class WebhookValidator:
    def validate_request(self, request: Request):
        # Check nonce (prevent replay)
        nonce = request.headers.get('X-Nonce')
        if self.is_nonce_used(nonce):
            raise ReplayAttackError("Nonce already used")
        self.mark_nonce_used(nonce, ttl=3600)  # 1 hour
        
        # Check timestamp (prevent old requests)
        timestamp = int(request.headers.get('X-Timestamp', 0))
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:  # 5 minutes
            raise ReplayAttackError("Request timestamp too old")
        
        # Validate signature
        signature = request.headers.get('X-Signature')
        if not self.verify_signature(request.body, signature):
            raise InvalidSignatureError("Invalid signature")
```

**Idempotency Keys - End-to-End Propagation**:
```python
class IdempotencyHandler:
    def process_request(self, request: Request):
        # Extract idempotency key from header
        idempotency_key = request.headers.get('Idempotency-Key')
        
        # Check if already processed
        if idempotency_key:
            cached_response = self.get_cached_response(idempotency_key)
            if cached_response:
                return cached_response
        
        # Process request with idempotency key propagated
        response = self.process_with_idempotency(request, idempotency_key)
        
        # Cache response
        if idempotency_key:
            self.cache_response(idempotency_key, response, ttl=86400)  # 24 hours
        
        return response
    
    def process_with_idempotency(self, request: Request, idempotency_key: str):
        """Process request with idempotency key propagated through pipeline"""
        # Step 1: Ingestion
        ticket_data = self.ingest_ticket(request, idempotency_key)
        
        # Step 2: Queue message (include idempotency key)
        queue_message = {
            'ticket_data': ticket_data,
            'idempotency_key': idempotency_key,  # Propagated to queue
            'timestamp': time.time()
        }
        self.publish_to_queue(queue_message)
        
        # Step 3: Processor (receive idempotency key from queue)
        processed_ticket = self.process_ticket(queue_message)
        
        # Step 4: Execution (if needed, include idempotency key)
        if processed_ticket.requires_execution:
            execution_result = self.execute_runbook(
                processed_ticket.runbook_id,
                idempotency_key=idempotency_key  # Propagated to execution
            )
        
        # Step 5: Ticket update (include idempotency key)
        self.update_ticket_status(
            processed_ticket.ticket_id,
            status='resolved',
            idempotency_key=idempotency_key  # Propagated to ticket update
        )
        
        return {
            'ticket_id': processed_ticket.ticket_id,
            'status': 'processed',
            'idempotency_key': idempotency_key
        }
```

**End-to-End Idempotency**:
- Idempotency key propagated through entire pipeline
- Ingestion → Queue → Processor → Execution → Ticket Updater
- Same idempotency key = same result at every step
- Idempotency key included in:
  - Queue message metadata
  - Execution session metadata
  - Ticket update API calls
  - All database operations

**Poison Message Policy**:
```python
class PoisonMessageHandler:
    def __init__(self):
        self.max_retries = 3
        self.dead_letter_queue = "tickets-poison-dlq"
    
    def handle_poison_message(self, message: dict, error: Exception):
        """Handle poison message with auto-quarantine"""
        retry_count = message.get('retry_count', 0)
        
        if retry_count < self.max_retries:
            # Retry with exponential backoff
            message['retry_count'] = retry_count + 1
            message['next_retry_at'] = time.time() + (2 ** retry_count) * 60
            self.requeue_message(message)
            return
        
        # Auto-quarantine after max retries
        self.quarantine_message(message, error)
        
        # Alert operator
        self.alert_operator({
            'message_id': message['id'],
            'error': str(error),
            'retry_count': retry_count,
            'requires_manual_review': True
        })
    
    def quarantine_message(self, message: dict, error: Exception):
        """Move message to dead-letter queue"""
        dlq_message = {
            'original_message': message,
            'error': str(error),
            'quarantined_at': time.time(),
            'requires_operator_action': True
        }
        
        self.publish_to_dlq(dlq_message)
        
        # Log quarantine event
        audit_log.record({
            'event': 'message_quarantined',
            'message_id': message['id'],
            'error': str(error),
            'retry_count': message.get('retry_count', 0)
        })
```

**Poison Message Runbook**:
```yaml
poison_message_runbook:
  detection:
    - max_retries_exceeded: 3
    - error_persists: true
    - validation_fails: true
  
  auto_quarantine:
    - move_to_dlq: true
    - log_quarantine_event: true
    - alert_operator: true
  
  operator_actions:
    1. review_message:
       - examine_message: original_message
       - check_error: error_details
       - verify_data_format: true
    
    2. fix_message:
       - correct_data_format: if_needed
       - validate_message: true
       - test_processing: true
    
    3. reprocess:
       - remove_from_dlq: true
       - republish_to_queue: true
       - monitor_processing: true
    
    4. discard:
       - document_reason: discard_reason
       - archive_message: true
       - update_metrics: false_positive_count
```

**Queue Message Metadata**:
```python
# Queue message structure with idempotency
queue_message = {
    'id': 'msg-12345',
    'idempotency_key': 'idemp-67890',  # End-to-end propagation
    'ticket_data': {...},
    'retry_count': 0,
    'created_at': time.time(),
    'metadata': {
        'source': 'webhook',
        'version': '1.0'
    }
}
```

#### 5.9.10 Message Queue Security (CRITICAL)

**TLS + Client Authentication**:
```yaml
# Kafka/RabbitMQ security
kafka:
  security:
    tls:
      enabled: true
      require_client_auth: true
      ca_certificate: "/etc/ssl/ca.crt"
      certificate: "/etc/ssl/client.crt"
      key: "/etc/ssl/client.key"
  
  acls:
    - principal: "CN=worker-1"
      resource: "topic:tickets"
      operation: "read"
    - principal: "CN=orchestrator"
      resource: "topic:tickets"
      operation: "write"
```

**Topic/Queue ACLs**:
- Per-service account permissions
- Read-only, write-only, or read-write
- Principle of least privilege

**Message Retention & Redaction**:
- Retention: 7 days for tickets, 30 days for executions
- Sensitive data redacted before storage
- Encryption at rest for message queues
- Automatic deletion after retention period

#### 5.9.11 Field-Level Data Protection (CRITICAL)

**Column/Field Encryption**:

**Sensitive Fields**:
- Ticket raw payloads (may contain PII)
- Infrastructure paths (may reveal topology)
- Command outputs (may contain secrets)
- Credential metadata

**Encryption Implementation**:
```python
# Field-level encryption
from cryptography.fernet import Fernet

class FieldEncryption:
    def __init__(self, tenant_id: int):
        # Get tenant-specific encryption key
        self.key = get_tenant_kms_key(tenant_id)
        self.cipher = Fernet(self.key)
    
    def encrypt_field(self, field_value: str) -> str:
        return self.cipher.encrypt(field_value.encode()).decode()
    
    def decrypt_field(self, encrypted_value: str) -> str:
        return self.cipher.decrypt(encrypted_value.encode()).decode()
```

**UI Masking**:
- Sensitive fields masked in UI
- Show only last 4 characters: `****1234`
- Blur effect for sensitive data
- "Show" button requires additional authentication

**Log Redaction**:
- PII detection and redaction in logs
- Regex patterns for common PII (SSN, email, phone)
- Automatic redaction before logging

**Legal Hold & Privacy Deletion**:

**Legal Hold Implementation**:
```python
class LegalHoldManager:
    def place_hold(self, resource_type: str, resource_id: str, case_id: str):
        """Place legal hold on resource"""
        hold = LegalHold(
            resource_type=resource_type,
            resource_id=resource_id,
            case_id=case_id,
            placed_at=datetime.now(),
            expires_at=None  # Legal holds don't expire automatically
        )
        db.session.add(hold)
        db.session.commit()
        
        # Mark resource as under legal hold
        self.mark_resource_held(resource_type, resource_id)
    
    def check_hold(self, resource_type: str, resource_id: str) -> bool:
        """Check if resource is under legal hold"""
        hold = db.session.query(LegalHold).filter(
            LegalHold.resource_type == resource_type,
            LegalHold.resource_id == resource_id,
            LegalHold.released_at.is_(None)
        ).first()
        return hold is not None
    
    def prevent_deletion(self, resource_type: str, resource_id: str):
        """Prevent deletion of resources under legal hold"""
        if self.check_hold(resource_type, resource_id):
            raise LegalHoldError("Resource is under legal hold and cannot be deleted")
```

**Privacy Deletion Paths**:
```python
class PrivacyDeletionManager:
    def delete_user_data(self, user_id: int, tenant_id: int):
        """Delete user data per privacy request"""
        # Check for legal holds
        if self.check_legal_holds(user_id, tenant_id):
            raise LegalHoldError("Cannot delete data under legal hold")
        
        # Anonymize audit logs
        self.anonymize_audit_logs(user_id, tenant_id)
        
        # Delete user records
        self.delete_user_records(user_id, tenant_id)
        
        # Delete execution sessions
        self.delete_execution_sessions(user_id, tenant_id)
        
        # Verify deletion
        self.verify_deletion(user_id, tenant_id)
    
    def anonymize_audit_logs(self, user_id: int, tenant_id: int):
        """Anonymize audit logs (don't delete for compliance)"""
        db.session.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.tenant_id == tenant_id
        ).update({
            'user_id': None,
            'ip_address': '[ANONYMIZED]',
            'user_agent': '[ANONYMIZED]'
        })
        db.session.commit()
```

**Key-Scoped Access in Analytics**:
```python
class AnalyticsDataAccess:
    def __init__(self):
        self.analytics_keys = {}  # Tenant-specific analytics keys
    
    def get_analytics_key(self, tenant_id: int) -> bytes:
        """Get tenant-specific analytics encryption key"""
        if tenant_id not in self.analytics_keys:
            # Derive analytics key from tenant KMS key
            tenant_key = get_tenant_kms_key(tenant_id)
            self.analytics_keys[tenant_id] = derive_analytics_key(tenant_key)
        return self.analytics_keys[tenant_id]
    
    def encrypt_analytics_data(self, data: dict, tenant_id: int) -> str:
        """Encrypt analytics data with tenant-specific key"""
        key = self.get_analytics_key(tenant_id)
        cipher = Fernet(key)
        return cipher.encrypt(json.dumps(data).encode()).decode()
    
    def decrypt_analytics_data(self, encrypted_data: str, tenant_id: int) -> dict:
        """Decrypt analytics data with tenant-specific key"""
        key = self.get_analytics_key(tenant_id)
        cipher = Fernet(key)
        return json.loads(cipher.decrypt(encrypted_data.encode()).decode())
```

**Vector Store & LLM Data Retention**:

**Vector Store Retention**:
```python
class VectorStoreRetention:
    def __init__(self):
        self.retention_policy = {
            'chunks': timedelta(days=365 * 7),  # 7 years
            'embeddings': timedelta(days=365 * 7),
            'documents': timedelta(days=365 * 7)
        }
    
    def delete_tenant_data(self, tenant_id: int):
        """Delete tenant's vector store data"""
        # Check for legal holds
        if self.check_legal_holds(tenant_id):
            raise LegalHoldError("Cannot delete data under legal hold")
        
        # Delete embeddings
        vector_store.delete_tenant_embeddings(tenant_id)
        
        # Delete chunks
        vector_store.delete_tenant_chunks(tenant_id)
        
        # Delete documents
        vector_store.delete_tenant_documents(tenant_id)
    
    def purge_expired_data(self):
        """Purge expired data per retention policy"""
        for data_type, retention in self.retention_policy.items():
            cutoff_date = datetime.now() - retention
            vector_store.delete_before_date(data_type, cutoff_date)
```

**LLM Prompt/Response Retention**:
```python
class LLMDataRetention:
    def __init__(self):
        self.retention_policy = {
            'prompts': timedelta(days=365),  # 1 year
            'responses': timedelta(days=365),
            'hashes': timedelta(days=365 * 7)  # 7 years (hashes only)
        }
    
    def delete_tenant_llm_data(self, tenant_id: int):
        """Delete tenant's LLM interaction data"""
        # Check for legal holds
        if self.check_legal_holds(tenant_id):
            raise LegalHoldError("Cannot delete data under legal hold")
        
        # Delete prompt/response hashes
        db.session.query(LLMInteraction).filter(
            LLMInteraction.tenant_id == tenant_id
        ).delete()
        db.session.commit()
    
    def purge_expired_interactions(self):
        """Purge expired LLM interactions"""
        cutoff_date = datetime.now() - self.retention_policy['prompts']
        db.session.query(LLMInteraction).filter(
            LLMInteraction.created_at < cutoff_date
        ).delete()
        db.session.commit()
```

**Cross-Tenant Safeguards**:
```python
class CrossTenantSafeguards:
    def verify_tenant_isolation(self, tenant_id: int, data: dict):
        """Verify data belongs to correct tenant"""
        if 'tenant_id' in data and data['tenant_id'] != tenant_id:
            raise SecurityError("Cross-tenant data access detected")
        
        # Verify RLS is enforced
        if not self.check_rls_enabled():
            raise SecurityError("RLS not enabled - security risk")
    
    def check_rls_enabled(self) -> bool:
        """Verify RLS is enabled on all tables"""
        tables = ['tickets', 'runbooks', 'execution_sessions', 'credentials']
        for table in tables:
            result = db.session.execute(text(
                f"SELECT relrowsecurity FROM pg_class WHERE relname = '{table}'"
            )).scalar()
            if not result:
                return False
        return True
```

#### 5.9.12 Data Lineage & Retention (CRITICAL)

**Data Lineage Map**:

```yaml
data_lineage:
  ticket_ingestion:
    sources:
      - monitoring_tools
      - webhooks
    flows_to:
      - ticket_analysis
      - runbook_resolution
    persisted_as:
      - tickets table
      - audit_logs
    retention: 2_years
  
  runbook_generation:
    sources:
      - ticket_analysis
      - vector_store
      - llm_provider
    flows_to:
      - runbook_storage
      - execution_engine
    persisted_as:
      - runbooks table
      - runbook_citations
    retention: 7_years  # Permanent retention
  
  execution:
    sources:
      - runbooks
      - credentials
      - infrastructure_connections
    flows_to:
      - execution_results
      - ticket_updates
      - analytics
    persisted_as:
      - execution_sessions
      - execution_steps
      - execution_outputs
    retention: 2_years
  
  outputs:
    sources:
      - command_execution
      - infrastructure_responses
    flows_to:
      - resolution_verification
      - ticket_comments
    persisted_as:
      - execution_steps.output
      - execution_results
    retention: 90_days  # Shorter retention for outputs
```

**Retention Policies**:
- Automatic deletion after retention period
- Archival to cold storage before deletion
- Compliance retention (extended for regulatory requirements)
- User-initiated deletion (with approval)

**TTL Per Object**:
```sql
-- Automatic cleanup
CREATE POLICY auto_delete_tickets ON tickets
    FOR DELETE
    USING (created_at < NOW() - INTERVAL '2 years');

CREATE POLICY auto_delete_execution_outputs ON execution_steps
    FOR UPDATE
    USING (output IS NOT NULL AND completed_at < NOW() - INTERVAL '90 days')
    SET output = '[REDACTED - Retention expired]';
```

#### 5.9.13 LLM Governance & Risk Controls (CRITICAL)

**Model Risk Controls**:

**Prompt & Response Logging**:
```python
class LLMGovernance:
    def __init__(self):
        self.token_limits = {
            'per_tenant': {
                'default': 100000,  # 100k tokens per day
                'premium': 1000000   # 1M tokens per day
            },
            'per_request': {
                'max_input_tokens': 8000,
                'max_output_tokens': 4000
            }
        }
        self.rate_limits = {
            'per_tenant': {
                'requests_per_minute': 60,
                'requests_per_hour': 1000
            }
        }
    
    def log_llm_interaction(self, prompt: str, response: str, model: str):
        # PII filter pre-prompt
        filtered_prompt = self.filter_pii(prompt)
        
        # Hash prompt and response for privacy
        prompt_hash = hashlib.sha256(filtered_prompt.encode()).hexdigest()
        response_hash = hashlib.sha256(response.encode()).hexdigest()
        
        audit_log.record({
            "event": "llm_interaction",
            "model": model,
            "model_version": get_model_version(model),
            "model_card": get_model_card(model),  # Model card pinning
            "prompt_hash": prompt_hash,
            "response_hash": response_hash,
            "prompt_length": len(filtered_prompt),
            "response_length": len(response),
            "tokens_used": self.count_tokens(filtered_prompt, response),
            "temperature": self.temperature,
            "seed": self.seed,
            "pii_filtered": prompt != filtered_prompt,
            "timestamp": datetime.now()
        })
    
    def filter_pii(self, text: str) -> str:
        """Remove PII from prompt before sending to LLM"""
        # Email patterns
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        # Phone numbers
        text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE_REDACTED]', text)
        # SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
        # IP addresses (optional, might be needed for troubleshooting)
        # text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]', text)
        return text
    
    def check_rate_limits(self, tenant_id: int) -> bool:
        """Check if tenant has exceeded rate limits"""
        # Check per-minute limit
        requests_last_minute = self.count_requests(tenant_id, minutes=1)
        if requests_last_minute >= self.rate_limits['per_tenant']['requests_per_minute']:
            return False
        
        # Check per-hour limit
        requests_last_hour = self.count_requests(tenant_id, minutes=60)
        if requests_last_hour >= self.rate_limits['per_tenant']['requests_per_hour']:
            return False
        
        return True
    
    def check_token_limits(self, tenant_id: int, tokens_used: int) -> bool:
        """Check if tenant has exceeded token limits"""
        tenant_limit = self.get_tenant_limit(tenant_id)
        tokens_today = self.count_tokens_today(tenant_id)
        
        if tokens_today + tokens_used > tenant_limit:
            return False
        
        return True
```

**Model Version Pinning**:
- Pin LLM model versions in configuration
- No automatic upgrades in production
- Change control process for model updates
- A/B testing for new models
- **Model Card Pinning**: Each model version has associated model card with capabilities, limitations, biases

**Model Card Structure**:
```yaml
model_card:
  version: "gpt-4-2024-11-06"
  capabilities:
    - ticket_classification
    - runbook_generation
    - false_positive_detection
  limitations:
    - may_hallucinate: true
    - requires_validation: true
  biases:
    - language_preference: english
  performance_metrics:
    ticket_classification_accuracy: 0.92
    runbook_generation_quality: 0.85
  rollback_trigger:
    - accuracy_drops_below: 0.80
    - latency_exceeds: 30_seconds
    - error_rate_exceeds: 0.05
```

**Safety Filters**:
- Content filtering for inappropriate content
- Toxicity detection
- PII detection in LLM outputs
- Refusal to generate harmful commands
- **Pre-prompt PII filtering**: Remove PII before sending to LLM

**Confidence Thresholds with No-Execute Gate**:
```python
confidence_thresholds = {
    "ticket_classification": {
        "auto_resolve": 0.95,  # Auto-resolve false positives
        "auto_execute": 0.90,  # Auto-execute runbook
        "human_review": 0.70,  # Below this, require human review
        "reject": 0.50  # Below this, reject and escalate
    },
    "runbook_generation": {
        "auto_approve": 0.85,
        "human_review": 0.70,
        "reject": 0.50
    },
    "destructive_actions": {
        "two_key_required": True,  # Require two approvals
        "min_confidence": 0.95,  # Even with approval, confidence must be high
        "no_execute_below": 0.90  # No execute if confidence < 0.90
    }
}

class NoExecuteGate:
    def check_execution_allowed(self, runbook: Runbook, confidence: float, 
                               approver_count: int) -> dict:
        """Check if execution is allowed based on confidence and approvals"""
        # Check for destructive actions
        has_destructive = self.has_destructive_actions(runbook)
        
        if has_destructive:
            # Two-key rule for destructive actions
            if approver_count < 2:
                return {
                    "allowed": False,
                    "reason": "Destructive actions require two approvals"
                }
            
            # Even with two approvals, confidence must be high
            if confidence < confidence_thresholds["destructive_actions"]["min_confidence"]:
                return {
                    "allowed": False,
                    "reason": f"Confidence {confidence} below minimum {confidence_thresholds['destructive_actions']['min_confidence']} for destructive actions"
                }
        
        # General confidence check
        if confidence < confidence_thresholds["destructive_actions"]["no_execute_below"]:
            return {
                "allowed": False,
                "reason": f"Confidence {confidence} below execution threshold"
            }
        
        return {"allowed": True}
```

**Drift Monitoring**:
- Monitor LLM output quality over time
- Detect degradation in performance
- Alert on significant changes
- Fallback to previous model version if drift detected

**Model Rollback Runbook**:
```yaml
model_rollback_runbook:
  trigger_conditions:
    - accuracy_drops_below_threshold: 0.80
    - latency_exceeds_threshold: 30_seconds
    - error_rate_exceeds_threshold: 0.05
    - drift_detected: true
  
  rollback_steps:
    1. detect_drift:
       - check_metrics: accuracy, latency, error_rate
       - compare_with_baseline: last_7_days
       - alert_if_degraded: true
    
    2. validate_rollback:
       - check_previous_model_available: true
       - verify_previous_model_metrics: better_than_current
       - get_approval: admin_approval_required
    
    3. execute_rollback:
       - switch_model_version: previous_stable_version
       - update_configuration: model_version
       - verify_model_health: check_health_endpoint
    
    4. monitor_after_rollback:
       - monitor_metrics: 24_hours
       - compare_performance: before_after
       - document_rollback_reason: incident_report
```

**Fallback Models**:
- Primary model: GPT-4 / Claude Opus
- Fallback model: GPT-3.5 / Claude Sonnet
- Emergency fallback: Local model (llama.cpp)
- Automatic failover on errors

#### 5.9.14 Observability & SRE Posture (CRITICAL)

**Distributed Tracing**:

**OpenTelemetry Integration**:
```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrument key operations
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("ticket_ingestion")
def ingest_ticket(ticket_data):
    # Ticket ingestion logic
    pass

@tracer.start_as_current_span("ticket_analysis")
def analyze_ticket(ticket_id):
    # Analysis logic
    pass
```

**Trace Coverage**:
- Ingestion → Analysis → Runbook Resolution → Execution → Verification
- End-to-end request tracing
- Service dependency mapping
- Performance bottleneck identification

**SLOs (Service Level Objectives)**:

```yaml
slos:
  ticket_ingestion:
    metric: p95_latency
    target: 5_seconds
    window: 30_days
  
  ticket_analysis:
    metric: p95_latency
    target: 30_seconds
    window: 30_days
  
  runbook_execution:
    metric: p95_step_time
    target: 10_seconds
    window: 30_days
  
  end_to_end_resolution:
    metric: p95_total_time
    target: 5_minutes
    window: 30_days
  
  availability:
    metric: uptime_percentage
    target: 99.9%
    window: 30_days
```

**MTTR (Mean Time To Recovery)**:
- Target: < 15 minutes for critical incidents
- Automated recovery procedures
- Runbook-driven incident response
- Post-mortem analysis

#### 5.9.15 Disaster Recovery Objectives (CRITICAL)

**RPO/RTO Per Component**:

```yaml
dr_objectives:
  database:
    rpo: 15_minutes  # Maximum data loss
    rto: 30_minutes  # Maximum downtime
    strategy: automated_replication
    backup_frequency: continuous
  
  vault:
    rpo: 5_minutes
    rto: 15_minutes
    strategy: vault_cluster
    backup_frequency: 5_minutes
  
  message_queue:
    rpo: 1_minute
    rto: 5_minutes
    strategy: cluster_replication
    backup_frequency: real_time
  
  agent_workers:
    rpo: 0_minutes  # Stateless
    rto: 5_minutes
    strategy: auto_scaling
    backup_frequency: n/a
  
  orchestrator:
    rpo: 1_minute
    rto: 10_minutes
    strategy: multi_zone_deployment
    backup_frequency: continuous
```

**Game Day Scenarios**:

**Scenario 1: Worker Pool Failure**:
- Simulate all workers offline
- Test auto-scaling
- Test failover to backup workers
- Measure RTO
- **Pass Criteria**: RTO < 5 minutes, no data loss

**Scenario 2: Vault Outage**:
- Simulate Vault unavailable
- Test credential caching
- Test fallback to backup vault
- Measure RTO
- **Vault Rehydration Test**: Verify credentials restored correctly
- **Pass Criteria**: RTO < 15 minutes, all credentials accessible

**Scenario 3: Ticketing API Brownout**:
- Simulate ticketing tool API failures
- Test request queuing
- Test retry logic
- Test graceful degradation
- **Pass Criteria**: Messages queued, no data loss, recovery < 5 minutes

**Scenario 4: Database Failure**:
- Simulate primary database failure
- Test failover to replica
- Test data consistency
- Measure RPO/RTO
- **Database Failover Consistency Check**: Verify no data corruption
- **Pass Criteria**: RPO < 15 minutes, RTO < 30 minutes, data consistency verified

**Quarterly Game-Day Playbooks**:

**Game Day Playbook Template**:
```yaml
game_day_playbook:
  name: "Worker Pool Failure"
  frequency: quarterly
  duration: 2_hours
  
  pre_game_checklist:
    - backup_all_data: true
    - notify_stakeholders: true
    - prepare_rollback_plan: true
  
  scenario_execution:
    1. isolate_workers:
       - stop_all_workers: true
       - verify_isolation: true
       - measure_detection_time: true
    
    2. test_auto_scaling:
       - trigger_auto_scale: true
       - verify_new_workers: true
       - measure_scaling_time: true
    
    3. test_failover:
       - activate_backup_workers: true
       - verify_connectivity: true
       - measure_failover_time: true
    
    4. verify_recovery:
       - check_system_health: true
       - verify_no_data_loss: true
       - measure_recovery_time: true
  
  measurable_pass_fail:
    - detection_time: < 1_minute
    - scaling_time: < 3_minutes
    - failover_time: < 5_minutes
    - recovery_time: < 5_minutes
    - data_loss: 0_bytes
    - failed_executions: 0
  
  post_game:
    - document_results: true
    - update_runbooks: if_needed
    - schedule_follow_up: if_failed
```

**Vault Outage Rehydration Test**:
```yaml
vault_rehydration_test:
  steps:
    1. backup_vault:
       - export_all_secrets: true
       - verify_backup_completeness: true
       - store_backup_securely: true
    
    2. simulate_outage:
       - stop_primary_vault: true
       - verify_outage: true
       - measure_detection_time: true
    
    3. failover_to_backup:
       - activate_backup_vault: true
       - verify_vault_connectivity: true
       - measure_failover_time: true
    
    4. rehydrate_credentials:
       - restore_all_secrets: true
       - verify_credential_access: true
       - test_credential_usage: true
       - measure_rehydration_time: true
    
    5. verify_integrity:
       - compare_secret_counts: backup_vs_restored
       - verify_no_secrets_missing: true
       - test_credential_functionality: true
  
  pass_criteria:
    - failover_time: < 5_minutes
    - rehydration_time: < 10_minutes
    - secrets_missing: 0
    - credential_functionality: 100%
```

**Database Failover Consistency Check**:
```yaml
database_failover_test:
  steps:
    1. prepare_test_data:
       - create_test_transactions: 100
       - verify_data_consistency: true
       - measure_replication_lag: true
    
    2. simulate_failure:
       - stop_primary_database: true
       - verify_failure_detection: true
       - measure_detection_time: true
    
    3. failover_to_replica:
       - promote_replica_to_primary: true
       - verify_database_connectivity: true
       - measure_failover_time: true
    
    4. consistency_check:
       - compare_row_counts: primary_vs_replica
       - verify_transaction_integrity: true
       - check_for_corruption: true
       - verify_replication_lag: < 15_minutes
    
    5. verify_rpo_rto:
       - calculate_data_loss: should_be_zero
       - measure_total_downtime: should_be_< 30_minutes
       - verify_all_transactions_replicated: true
  
  pass_criteria:
    - rpo_achieved: true  # No data loss
    - rto_achieved: true  # Recovery < 30 minutes
    - data_consistency: 100%
    - corruption_detected: false
```

**DR Runbooks**:
- Documented procedures for each scenario
- **Quarterly drills** (measurable pass/fail criteria)
- Lessons learned incorporated
- Automation improvements
- **RPO/RTO Evidence**: Documented proof of meeting objectives

---

## 5.10 Security Gap Summary

| Gap | Status | Criticality | Addressed In |
|-----|--------|------------|--------------|
| DB-level tenant isolation (RLS) | ✅ Addressed | CRITICAL | Section 5.9.1 |
| Break-glass & emergency access | ✅ Addressed | CRITICAL | Section 5.9.2 |
| Service account sprawl | ✅ Addressed | CRITICAL | Section 5.9.3 |
| Credential bootstrap ("secret zero") | ✅ Addressed | CRITICAL | Section 5.9.4 |
| On-worker secret exposure | ✅ Addressed | CRITICAL | Section 5.9.5 |
| Command execution guardrails | ✅ Addressed | CRITICAL | Section 5.9.6 |
| Sandboxing & isolation | ✅ Addressed | CRITICAL | Section 5.9.7 |
| Image integrity & provenance | ✅ Addressed | CRITICAL | Section 5.9.8 |
| Agent upgrade trust | ✅ Addressed | CRITICAL | Section 5.9.8 |
| Webhook replay & idempotency | ✅ Addressed | CRITICAL | Section 5.9.9 |
| Queue security | ✅ Addressed | CRITICAL | Section 5.9.10 |
| Field-level data protection | ✅ Addressed | CRITICAL | Section 5.9.11 |
| Data lineage & retention | ✅ Addressed | CRITICAL | Section 5.9.12 |
| LLM governance | ✅ Addressed | CRITICAL | Section 5.9.13 |
| Distributed tracing & SLOs | ✅ Addressed | CRITICAL | Section 5.9.14 |
| DR objectives (RPO/RTO) | ✅ Addressed | CRITICAL | Section 5.9.15 |

**Authentication**:
- ✅ MFA for all admin and operator accounts
- ✅ SSO integration (SAML 2.0, OIDC)
- ✅ OAuth 2.0 with JWT for API access
- ✅ Certificate-based authentication for workers
- ✅ Session timeout and secure session management

**Authorization**:
- ✅ RBAC with least privilege principle
- ✅ ABAC for fine-grained access control
- ✅ JIT access for elevated permissions
- ✅ Regular access reviews

**Credentials**:
- ✅ Never store credentials in code
- ✅ Vault integration for credential storage
- ✅ Automatic credential rotation
- ✅ Credential access auditing
- ✅ Zero-downtime rotation

**Network**:
- ✅ Network segmentation
- ✅ TLS 1.3 for all connections
- ✅ Firewall rules and ACLs
- ✅ VPN for remote access
- ✅ Encrypted backups

**Application**:
- ✅ Input validation and sanitization
- ✅ Output encoding
- ✅ Rate limiting
- ✅ Security headers
- ✅ Regular security testing

**Monitoring**:
- ✅ Comprehensive audit logging
- ✅ Real-time security monitoring
- ✅ Anomaly detection
- ✅ Incident response procedures
- ✅ Regular security assessments

---

## 6. API Design

### 6.1 Ticket Ingestion API

```python
POST /api/v1/tickets/ingest
Body: {
    "source": "prometheus",
    "ticket_id": "INC-12345",
    "title": "Database connection pool exhausted",
    "description": "...",
    "severity": "high",
    "environment": "prod",
    "service": "postgresql",
    "metadata": {...}
}
Response: {
    "ticket_id": "INC-12345",
    "status": "analyzing",
    "analysis_id": "analysis-123"
}

# Update ticket status back to ticketing tool
POST /api/v1/tickets/{ticket_id}/update-status
Body: {
    "status": "resolved",
    "comment": "Issue resolved via automated runbook execution",
    "resolution_details": {...}
}
# This calls ServiceNow/Jira API to update ticket status
```

### 6.2 Ticket Analysis API

```python
GET /api/v1/tickets/{ticket_id}/analysis
Response: {
    "classification": "true_positive",
    "confidence": 0.92,
    "reasoning": "...",
    "requires_human_review": false
}

POST /api/v1/tickets/{ticket_id}/analyze
Response: {
    "analysis_id": "analysis-123",
    "classification": "false_positive",
    "confidence": 0.95
}
```

### 6.3 Execution API

```python
POST /api/v1/executions/{session_id}/approve
Body: {
    "step_number": 3,
    "approved": true,
    "notes": "Output looks good"
}

POST /api/v1/executions/{session_id}/reject
Body: {
    "step_number": 3,
    "reason": "Output shows unexpected error",
    "escalate": true
}

POST /api/v1/executions/{session_id}/step/{step_number}/execute
Body: {
    "approve": true,  # Auto-approve if human already approved
    "agent_worker_id": "worker-1"  # Optional: specify worker
}
Response: {
    "execution_id": "exec-123",
    "success": true,
    "output": "...",
    "requires_approval": false,
    "agent_worker_id": "worker-1",
    "execution_time": 2.5
}

# Internal execution stream (for our UI only, not external broadcast)
WS /api/v1/executions/{session_id}/stream
# Subscribe to execution updates (internal use only)
# Messages:
#   - execution.step_started
#   - execution.step_output  # Real-time stdout/stderr
#   - execution.step_completed
#   - execution.requires_approval
#   - execution.completed
#   - execution.failed
```

### 6.5 Agent Worker API

```python
# Internal API for agent workers
POST /api/v1/agent/register
Body: {
    "worker_id": "worker-1",
    "name": "Production Worker VPC-A",
    "network_segment": "VPC-A",
    "capabilities": ["ssh", "database", "api"],
    "max_load": 10,
    "hostname": "worker-1.internal",
    "ip_address": "10.0.1.100"
}

POST /api/v1/agent/heartbeat
Body: {
    "worker_id": "worker-1",
    "status": "active",
    "current_load": 3
}

GET /api/v1/agent/workers
Query: ?network_segment=VPC-A&status=active
Response: {
    "workers": [
        {
            "worker_id": "worker-1",
            "status": "active",
            "current_load": 3,
            "max_load": 10,
            "capabilities": ["ssh", "database"]
        }
    ]
}
```

### 6.4 Credential Management API

```python
POST /api/v1/credentials
Body: {
    "name": "prod-db-postgres",
    "type": "database",
    "vault_path": "secret/data/infrastructure/prod/postgres",
    "environment": "prod",
    "service": "postgresql"
}

GET /api/v1/credentials/{credential_id}/access
# Returns access audit log (no credential values)
```

---

## 7. Infrastructure Connectors

### 7.1 SSH Connector

```python
class SSHConnector(InfrastructureConnector):
    async def connect(self, credentials: Credentials) -> Connection:
        # Use paramiko or asyncssh
        # Key-based auth preferred
        # Support password auth as fallback
    
    async def execute_command(self, command: str, timeout: int) -> ExecutionResult:
        # Execute command via SSH
        # Capture stdout/stderr
        # Handle timeouts
        # Return structured result
```

**Security**:
- Host key verification
- Key-based authentication
- Connection timeout
- Command timeout
- Output sanitization

### 7.2 Database Connector

```python
class DatabaseConnector(InfrastructureConnector):
    async def connect(self, credentials: Credentials) -> Connection:
        # Use async database drivers
        # TLS required
        # Connection pooling
    
    async def execute_command(self, command: str, timeout: int) -> ExecutionResult:
        # Execute SQL query
        # Handle transactions
        # Return results
```

**Supported Databases**:
- PostgreSQL (asyncpg)
- MySQL (aiomysql)
- MSSQL (aioodbc)
- MongoDB (motor)
- Redis (aioredis)

### 7.3 Kubernetes Connector

```python
class KubernetesConnector(InfrastructureConnector):
    async def connect(self, credentials: Credentials) -> Connection:
        # Use kubernetes Python client
        # Load kubeconfig from vault
        # Authenticate via service account
    
    async def execute_command(self, command: str, timeout: int) -> ExecutionResult:
        # Execute kubectl commands
        # Or use Kubernetes API directly
        # Return results
```

### 7.4 Cloud API Connectors

**AWS Connector**:
- Use boto3 with IAM roles
- Support for EC2, RDS, S3, Lambda, etc.
- Region-aware execution

**Azure Connector**:
- Use Azure SDK
- Service principal authentication
- Resource group scoping

**GCP Connector**:
- Use GCP SDK
- Service account authentication
- Project scoping

---

## 8. Human-in-the-Loop Workflow

### 8.1 Execution Modes

**Mode 1: Per-Step Approval**
- Human approves each step before execution
- Maximum safety, slower execution
- Use for critical systems

**Mode 2: Per-Phase Approval**
- Human approves after prechecks, before main steps, after main steps
- Balanced safety and speed
- Default mode

**Mode 3: Critical-Only Approval**
- Auto-approve non-critical steps
- Human approval only for critical steps
- Faster execution

**Mode 4: Final Approval Only**
- Auto-execute all steps
- Human approval only at the end
- Fastest execution

### 8.2 Approval Workflow

```
Step Ready → Check Approval Required → Check Auto-Approve Threshold
                                         ├─ Auto-Approve (confidence > threshold)
                                         │   └─ Execute Step
                                         └─ Requires Approval
                                             ├─ Notify Human (Slack/Email/UI)
                                             ├─ Wait for Approval (with timeout)
                                             └─ Execute if Approved
```

**Notification Channels**:
- Real-time: WebSocket, Server-Sent Events
- Push: Slack, Microsoft Teams
- Email: For non-critical approvals
- UI: Dashboard with pending approvals

**Approval Timeout**:
- Default: 15 minutes
- Critical: 5 minutes
- Non-critical: 30 minutes
- Configurable per runbook

### 8.3 Rollback Mechanism

**Trigger Conditions**:
- Step execution failure
- Human rejection
- Postcheck failure
- Timeout

**Rollback Process**:
```
Failure Detected → Check Rollback Available → Execute Rollback Steps
                                                ├─ Success → Mark Session Failed
                                                └─ Failure → Escalate
```

**Rollback Steps**:
- Defined in runbook metadata
- Reverse order execution
- Human approval may be required

---

## 9. Monitoring & Observability

### 9.1 Metrics

**Ticket Metrics**:
- Tickets received per hour/day
- False positive rate
- True positive rate
- Analysis accuracy

**Execution Metrics**:
- Execution success rate
- Average execution time
- Steps per execution
- Human approval rate
- Auto-approval rate

**Infrastructure Metrics**:
- Connection success rate
- Command execution time
- Connection pool usage
- Credential access rate

**Agent Metrics**:
- Active executions
- Queue depth
- Processing latency
- Error rate

### 9.2 Logging

**Log Levels**:
- **DEBUG**: Detailed execution logs
- **INFO**: Normal operations
- **WARNING**: Recoverable errors
- **ERROR**: Execution failures
- **CRITICAL**: System failures

**Structured Logging**:
```json
{
    "timestamp": "2025-11-05T16:00:00Z",
    "level": "INFO",
    "service": "execution-engine",
    "execution_session_id": 123,
    "step_number": 3,
    "command": "SELECT * FROM ...",
    "infrastructure_type": "database",
    "connection_id": "prod-db-1",
    "duration_ms": 250,
    "success": true
}
```

### 9.3 Alerting

**Alert Conditions**:
- Execution failure rate > 10%
- Average execution time > threshold
- Queue depth > threshold
- Credential access failures
- Infrastructure connection failures

**Alert Channels**:
- PagerDuty
- Slack
- Email
- Custom webhooks

---

## 10. Database Schema Updates

### 10.1 New Tables

```sql
-- Tickets table
CREATE TABLE tickets (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    source VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(20),
    environment VARCHAR(50),
    service VARCHAR(100),
    status VARCHAR(50) DEFAULT 'open',
    analysis JSONB,
    runbook_id INTEGER REFERENCES runbooks(id),
    execution_session_id INTEGER REFERENCES execution_sessions(id),
    resolution_confirmed BOOLEAN DEFAULT FALSE,
    false_positive BOOLEAN DEFAULT FALSE,
    suppressed_alerts JSONB,
    raw_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    escalated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tickets_tenant ON tickets(tenant_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_source ON tickets(source);
CREATE INDEX idx_tickets_created ON tickets(created_at);

-- Credentials table
CREATE TABLE credentials (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    vault_path VARCHAR(500) NOT NULL,
    environment VARCHAR(50),
    service VARCHAR(100),
    last_rotated TIMESTAMP WITH TIME ZONE,
    rotation_policy JSONB,
    access_policy JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name, environment)
);

CREATE INDEX idx_credentials_tenant ON credentials(tenant_id);
CREATE INDEX idx_credentials_type ON credentials(type);

-- Infrastructure connections table
CREATE TABLE infrastructure_connections (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    host VARCHAR(255),
    port INTEGER,
    credential_id VARCHAR(255) REFERENCES credentials(id),
    connection_params JSONB,
    health_check_enabled BOOLEAN DEFAULT TRUE,
    last_health_check TIMESTAMP WITH TIME ZONE,
    is_healthy BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_connections_tenant ON infrastructure_connections(tenant_id);
CREATE INDEX idx_connections_type ON infrastructure_connections(type);
CREATE INDEX idx_connections_health ON infrastructure_connections(is_healthy);

-- Audit logs table (enhanced)
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
```

### 10.2 Enhanced Tables

```sql
-- Enhance execution_sessions
ALTER TABLE execution_sessions
ADD COLUMN ticket_id VARCHAR(255) REFERENCES tickets(id),
ADD COLUMN validation_mode VARCHAR(50) DEFAULT 'per_phase',
ADD COLUMN human_approved BOOLEAN DEFAULT FALSE,
ADD COLUMN human_approver_id INTEGER REFERENCES users(id),
ADD COLUMN human_approved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN auto_approved BOOLEAN DEFAULT FALSE,
ADD COLUMN escalation_reason TEXT,
ADD COLUMN infrastructure_connections JSONB,
ADD COLUMN credentials_used JSONB,
ADD COLUMN agent_worker_id VARCHAR(255) REFERENCES agent_workers(id);

-- Enhance execution_steps
ALTER TABLE execution_steps
ADD COLUMN human_approved BOOLEAN DEFAULT FALSE,
ADD COLUMN human_approver_id INTEGER REFERENCES users(id),
ADD COLUMN human_approved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN auto_approved BOOLEAN DEFAULT FALSE,
ADD COLUMN requires_approval BOOLEAN DEFAULT FALSE,
ADD COLUMN execution_result JSONB,
ADD COLUMN infrastructure_type VARCHAR(50),
ADD COLUMN connection_id VARCHAR(255),
ADD COLUMN rollback_executed BOOLEAN DEFAULT FALSE,
ADD COLUMN rollback_result JSONB;
```

---

## 11. Implementation Phases

### Phase 2.1: Foundation (Weeks 1-2)
- [ ] Ticket ingestion service with webhook support
- [ ] Ticket status update client (ServiceNow/Jira API integration)
- [ ] Ticket analysis engine (LLM-based)
- [ ] Database schema updates (tickets, agent_workers)
- [ ] Basic API endpoints
- [ ] Enterprise authentication (SSO, MFA, OAuth 2.0)

### Phase 2.2: Agent Worker Infrastructure (Weeks 3-4)
- [ ] Agent worker framework (registration, heartbeat, health checks)
- [ ] Agent worker API (internal)
- [ ] Worker selection logic (network-aware, load balancing)
- [ ] Credential vault integration
- [ ] Connection management with patterns (direct, bastion, VPN)

### Phase 2.3: Infrastructure Connectors (Weeks 5-6)
- [ ] SSH connector (with bastion support)
- [ ] Database connectors (PostgreSQL, MySQL, MSSQL)
- [ ] Kubernetes connector
- [ ] Cloud API connectors (AWS, Azure, GCP)
- [ ] Connection pooling and lifecycle management

### Phase 2.4: Execution Engine (Weeks 7-8)
- [ ] Execution orchestrator
- [ ] Command executor (via agent workers)
- [ ] Real-time output streaming
- [ ] Output capture & analysis
- [ ] Basic rollback mechanism

### Phase 2.5: Human-in-the-Loop (Weeks 9-10)
- [ ] Validation checkpoint manager
- [ ] Approval workflow
- [ ] Internal notification system (WebSocket for UI only)
- [ ] UI for approvals with real-time updates
- [ ] Approval timeout handling

### Phase 2.6: Resolution & Escalation (Weeks 11-12)
- [ ] Resolution verification service
- [ ] Escalation service
- [ ] Alert suppression
- [ ] Integration with monitoring tools (webhook callbacks)
- [ ] Ticket status update to ticketing tools (ServiceNow/Jira API)

### Phase 2.7: Security & Compliance (Weeks 13-14)
- [ ] Enhanced audit logging
- [ ] RBAC and ABAC implementation
- [ ] SSO integration (SAML 2.0, OIDC)
- [ ] MFA implementation
- [ ] Network security hardening
- [ ] Worker authentication and authorization
- [ ] Security monitoring and incident response
- [ ] Compliance documentation (SOC 2, GDPR, etc.)

---

## 12. Security Best Practices

### 12.1 Credential Management
- ✅ Never store credentials in code
- ✅ Use enterprise vault (HashiCorp Vault preferred)
- ✅ Rotate credentials regularly
- ✅ Use least privilege principle
- ✅ Audit all credential access
- ✅ Encrypt credentials at rest and in transit

### 12.2 Command Execution
- ✅ Sanitize all inputs
- ✅ Use parameterized commands
- ✅ Implement command timeout
- ✅ Log all commands (sanitized)
- ✅ Prevent command injection
- ✅ Validate command outputs

### 12.3 Network Security
- ✅ TLS 1.3 for all connections
- ✅ SSH key-based authentication
- ✅ IP whitelisting where possible
- ✅ VPN for internal infrastructure
- ✅ Network segmentation

### 12.4 Access Control
- ✅ Role-based access control (RBAC)
- ✅ Multi-factor authentication (MFA)
- ✅ Session management
- ✅ Principle of least privilege
- ✅ Regular access reviews

---

## 13. Testing Strategy

### 13.1 Unit Tests
- Ticket analysis logic
- Command execution
- Credential handling
- Output parsing

### 13.2 Integration Tests
- Infrastructure connectors
- Vault integration
- Database operations
- API endpoints

### 13.3 End-to-End Tests
- Full ticket flow
- Execution with approval
- Escalation flow
- Rollback mechanism

### 13.4 Security Tests
- Credential access
- Command injection
- Authentication bypass
- Authorization checks

---

## 14. Deployment Considerations

### 14.1 High Availability
- Multi-instance deployment
- Load balancing
- Database replication
- Message queue clustering

### 14.2 Scalability
- Horizontal scaling
- Connection pooling
- Async processing
- Caching strategy

### 14.3 Disaster Recovery
- Database backups
- Configuration backups
- Credential vault backups
- Recovery procedures

---

## 15. Next Steps

1. **Review & Approval**: Review this architecture document
2. **Vault Setup**: Set up credential vault (HashiCorp Vault recommended)
3. **Infrastructure Assessment**: Inventory infrastructure components to connect
4. **Security Review**: Security team review of architecture
5. **POC Implementation**: Start with Phase 2.1 (Foundation)

---

## Appendix A: Technology Stack

### Backend
- **Framework**: FastAPI (Python) - Aligned with ARCHITECTURE.md
- **Database**: PostgreSQL + pgvector (POC) - Aligned with ARCHITECTURE.md
- **Message Queue**: RabbitMQ or Apache Kafka (Phase 2 addition)
- **Vault**: HashiCorp Vault (or AWS Secrets Manager / Azure Key Vault)
- **SSH**: asyncssh or paramiko
- **Database Drivers**: asyncpg, aiomysql, aioodbc
- **LLM Provider**: Pluggable provider abstraction (llama.cpp, OpenAI, Claude) - Aligned with ARCHITECTURE.md

### Frontend
- **Framework**: Next.js (React + TypeScript) - Aligned with ARCHITECTURE.md
- **Real-time**: WebSocket or Server-Sent Events
- **UI Components**: Tailwind CSS + Headless UI

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (production)
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or Loki

**Note**: This aligns with ARCHITECTURE.md's modular design principles and tech stack choices.

---

## Appendix B: Glossary

- **Ticket**: Incident or alert from monitoring tool
- **False Positive**: Alert that doesn't require action
- **True Positive**: Alert that requires troubleshooting
- **Runbook**: Automated troubleshooting procedure
- **Execution Session**: Single runbook execution instance
- **Validation Checkpoint**: Point where human approval is required
- **Escalation**: Transfer to human operator
- **Resolution Verification**: Confirmation that issue is resolved

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-05  
**Status**: Draft for Review

