# Troubleshooting AI Agent - Architecture

## Core Principle
**Modular Design**: POC with Postgres+pgvector, production-ready for Postgres+Qdrant swap

## Data Flow

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
LLM (Open-source: LLaMA 3.1 via Ollama - local, free)
        ↓
Runbook Generation/Update + Citations
```

## Tech Stack (All Open-Source, Zero Cost)

### POC Phase (v1)
- **Postgres + pgvector**: Everything in one database
- **sentence-transformers**: Local embeddings (E5-large-v2 or all-mpnet-base-v2)
- **Ollama + LLaMA 3.1 8B**: Local LLM
- **FastAPI**: Backend API
- **React + TypeScript**: Frontend

### Production Phase (v2)
- **Postgres**: Users, tenants, runbooks, audit logs
- **Qdrant**: Vector embeddings and search
- **Same LLM/Embedding stack**: No API costs

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

-- Execution logs
executions(id, tenant_id, runbook_id, status, logs TEXT, metadata JSONB, created_at)

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
- **Multi-tenant**: Isolated data per organization
