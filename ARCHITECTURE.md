# Troubleshooting AI Agent - Architecture

## Core Principle
**Modular Design**: POC with Postgres+pgvector, production-ready for Postgres+Qdrant swap

## Data Flow

### Phase 1: Assistant (Runbook Generation)
```
Data Sources (Slack, Confluence, Wiki, Logs, ServiceNow, Jira)
        ↓
Text Preprocessing + Chunking (512–1024 tokens)
        ↓
Embedding (Open-source: E5-large-v2 or all-mpnet-base-v2)
        ↓
Vector Store (Postgres+pgvector for POC, Qdrant for production)
        ↓
Retriever (semantic search + reranker: cross-encoder)
        ↓
LLM Provider (pluggable): POC uses llama.cpp (local, OpenAI-compatible). Providers can be swapped (e.g., OpenAI, Claude, others) via configuration.
        ↓
Runbook Generation/Update + Citations
```

### Phase 2: Human-in-the-Loop Agent (Execution Flow)
```
Monitoring Tools (Prometheus, Datadog, New Relic, PagerDuty)
        ↓
Ticket Ingestion → Ticket Analysis (False Positive Detection)
        ↓
Runbook Resolution (Semantic Search or Generation)
        ↓
Human-in-the-Loop Execution Engine
        ├─ Infrastructure Connectors (SSH, Databases, APIs, Cloud)
        ├─ Credential Vault (Secure credential management)
        ├─ Human Validation Checkpoints
        └─ Output Capture & Analysis
        ↓
Resolution Verification → Ticket Closure or Escalation
```

## Tech Stack (All Open-Source, Zero Cost)

### POC Phase (v1) - Phase 1: Assistant
- **Postgres + pgvector**: Everything in one database
- **sentence-transformers**: Local embeddings (E5-large-v2 or all-mpnet-base-v2)
- **llama.cpp**: Local LLM server (Qwen2.5 1.5B in POC); OpenAI-compatible API
- **FastAPI**: Backend API
- **Next.js (React + TypeScript)**: Frontend

### Phase 2: Human-in-the-Loop Agent (Current Focus)
- **Postgres + pgvector**: Runbooks, execution sessions, tickets, audit logs
- **Message Queue**: RabbitMQ or Apache Kafka for ticket ingestion
- **Credential Vault**: HashiCorp Vault (or AWS Secrets Manager / Azure Key Vault)
- **Infrastructure Connectors**: SSH (asyncssh), Database drivers (asyncpg, aiomysql, aioodbc), Cloud SDKs (boto3, Azure SDK, GCP SDK)
- **LLM Provider Abstraction**: Swap providers (OpenAI, Claude, local llama.cpp) via config without code changes
- **FastAPI**: Backend API with WebSocket support for real-time approvals
- **Next.js**: Frontend with real-time approval UI

### Production Phase (v2) - Future
- **Postgres**: Users, tenants, runbooks, execution sessions, tickets, audit logs
- **Qdrant**: Vector embeddings and search (migration from pgvector)
- **LLM Provider Abstraction**: Swap providers (OpenAI, Claude, local llama.cpp) via config without code changes
- **Scalable Architecture**: Kubernetes orchestration, horizontal scaling

## Database Schema (Postgres + pgvector)

### Core Tables
```sql
-- Tenants (multi-tenant support)
tenants(id, name, created_at)

-- Users and authentication
users(id, tenant_id, email, password_hash, role, created_at)

-- Source documents
documents(id, tenant_id, source_type, title, path, content_hash, metadata JSONB, created_at, updated_at)

-- Text chunks for embedding
chunks(id, document_id, text, chunk_hash, metadata JSONB, created_at)

-- Vector embeddings (pgvector)
embeddings(id, chunk_id, embedding VECTOR(384), created_at)

-- Generated runbooks
runbooks(id, tenant_id, title, body_md TEXT, metadata JSONB, confidence NUMERIC, parent_version_id, created_at, updated_at)

-- Execution logs (legacy, for Phase 1)
executions(id, tenant_id, runbook_id, status, logs TEXT, metadata JSONB, created_at)

-- Execution sessions (Phase 2: Human-in-the-Loop)
execution_sessions(id, tenant_id, runbook_id, ticket_id, status, validation_mode, human_approved, ...)

-- Execution steps (Phase 2: Human-in-the-Loop)
execution_steps(id, session_id, step_number, step_type, command, completed, success, output, human_approved, execution_result, ...)

-- Tickets (Phase 2: Ticket ingestion)
tickets(id, tenant_id, source, title, description, severity, environment, service, status, analysis, runbook_id, ...)

-- Credentials (Phase 2: Secure credential management)
credentials(id, tenant_id, name, type, vault_path, environment, service, ...)

-- Infrastructure connections (Phase 2: Infrastructure access)
infrastructure_connections(id, tenant_id, name, type, host, port, credential_id, ...)

-- Audit trail
audits(id, tenant_id, actor, action, entity, entity_id, diff JSONB, created_at)
```

## Modular Design Principles

### Vector Store Abstraction
```python
class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(self, chunks: List[Chunk]) -> None
    @abstractmethod
    def search(self, query: str, tenant_id: str, top_k: int) -> List[SearchResult]
    @abstractmethod
    def delete_by_document(self, document_id: str) -> None

class PgVectorStore(VectorStore):
    # Postgres + pgvector implementation

class QdrantVectorStore(VectorStore):
    # Qdrant implementation (future)
```

### Ingestion Pipeline
- **Normalized Document Schema**: Common format for all sources
- **Chunking Strategy**: 512-1024 tokens, 20-30% overlap
- **Deduplication**: Content hashes prevent duplicates
- **Update Logic**: Changed content updates existing chunks

### Runbook Management
- **Create vs Update**: Similarity threshold determines new vs update
- **Versioning**: Track changes with parent_version_id
- **Citations**: Link back to source chunks and documents
- **Confidence Scoring**: Based on retrieval quality and LLM consistency

## Migration Path (POC → Production)

1. **Export from Postgres**: `SELECT chunk_id, text, metadata, embedding FROM embeddings JOIN chunks`
2. **Import to Qdrant**: Bulk load with same IDs and payloads
3. **Switch Provider**: Change VectorStore implementation via config
4. **Zero Code Changes**: Application layer remains unchanged

## Key Features

### Ingestion Sources
- **Slack**: JSON export with thread grouping
- **Tickets**: CSV from ServiceNow/Jira
- **Logs**: Plain text with error grouping
- **Docs**: Markdown/HTML from Confluence

### Runbook Intelligence
- **Smart Updates**: Detect similar incidents, update existing runbooks
- **Structured Output**: Prerequisites, steps, verification, rollback
- **Citations**: Link to source documents and specific chunks
- **Version Control**: Track all changes with audit trail

### Web Interface
- **File Upload**: Drag-and-drop for all supported formats
- **Search**: Semantic search with filters and citations
- **Runbook Management**: View, edit, version, export runbooks
- **Execution Dashboard**: Real-time execution monitoring and approval UI
- **Ticket Management**: View and manage tickets from monitoring tools
- **Multi-tenant**: Isolated data per organization

### Phase 2: Agent Capabilities
- **Ticket Ingestion**: Webhook-based integration with monitoring tools
- **False Positive Detection**: LLM-based analysis to filter noise
- **Infrastructure Access**: Secure connections to servers, databases, cloud services
- **Human Validation**: Approval checkpoints at critical steps
- **Resolution Verification**: Automatic verification of issue resolution
- **Escalation**: Automatic escalation when automation fails

## Operational Modes (3-Phase)

- **Phase 1: Assistant (Draft Creation)**: If a matching runbook doesn't exist, the system performs RAG (semantic retrieval) and prompts the LLM provider to generate an agent-executable YAML runbook draft following the standard schema. Draft runbooks are reviewed and optionally edited by humans. Upon approval, the runbook is versioned and marked active for execution.

- **Phase 2: Human-in-the-Loop Agent (Execution with Validation)**: Approved runbooks are executed by the agent with human validation checkpoints. The agent:
  - Receives tickets from monitoring tools
  - Analyzes tickets for false positives vs true positives
  - Finds or generates appropriate runbooks
  - Executes runbooks step-by-step with human approval at checkpoints
  - Connects to infrastructure securely (SSH, databases, APIs, cloud services)
  - Verifies resolution and either closes tickets or escalates
  - All operations are logged and audited

- **Phase 3: Autonomous Bot (Full Automation)**: Approved runbooks are executed fully automatically with guardrails. Results, outputs, and audit logs are captured; failures trigger escalation or rollback. Human intervention only on exceptions or low-confidence scenarios.

## LLM Provider Abstraction

- The backend uses a provider interface to call an OpenAI-compatible chat API.
- POC: llama.cpp locally (http://localhost:8080) with a small GGUF model.
- Future: switch to providers such as OpenAI or Claude by changing configuration (API base URL/keys) without altering application logic.
