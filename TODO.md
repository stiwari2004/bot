# Troubleshooting AI Agent - TODO List

## Phase 1: Foundation (Postgres + pgvector, Open-source only)

### 1.1 System Scaffolding
- [ ] Create backend (FastAPI) and web (React) apps
- [ ] Docker Compose: Postgres (with pgvector), API, Web, (optional) Ollama
- [ ] Env/config management per-tenant (no hardcoded creds)
- [ ] Project structure: `backend/`, `frontend/`, `docker-compose.yml`

### 1.2 Data Model (Postgres)
- [ ] Create Postgres schema with pgvector extension
- [ ] Tables: tenants, users, documents, chunks, embeddings, runbooks, executions, audits
- [ ] Indices: embeddings ivfflat/hnsw, document foreign keys, created_at
- [ ] Content hashes for dedupe: document_hash, chunk_hash
- [ ] Migration scripts for schema changes

### 1.3 Vector Store Abstraction
- [ ] Define `VectorStore` interface
- [ ] Implement `PgVectorStore` (knn, upsert, delete by doc, search with filters)
- [ ] Keep provider-agnostic for later swap (Qdrant)
- [ ] Unit tests for vector operations

## Phase 2: Ingestion (Slack, Tickets, Logs, Docs)

### 2.1 Normalization Contracts
- [ ] Common "normalized document" schema: {source_type, title, content, metadata, tenant_id}
- [ ] Standardize timestamps, authors, channels, ticket IDs
- [ ] Validation schemas for each source type

### 2.2 Connectors (file-based to start; no vendor API)
- [ ] Slack JSON export (thread grouping; keep links/mentions)
- [ ] Tickets CSV (ServiceNow/Jira export shapes; map to fields)
- [ ] Logs (plain text; error window grouping)
- [ ] Docs (Markdown/Text; Confluence export md/html→md)
- [ ] File upload API endpoints

### 2.3 Processing Pipeline
- [ ] Cleaning: strip noise, preserve code/commands
- [ ] Chunking: 512–1024 tokens, 20–30% overlap; structural-first, semantic fallback
- [ ] Embeddings: sentence-transformers (local), batch encode
- [ ] Upsert logic:
  - [ ] New document → insert doc, chunks, embeddings
  - [ ] Existing (hash match) → skip
  - [ ] Changed (hash mismatch) → soft-retire old chunks, insert new; audit entry
- [ ] Metadata captured: source, path, author, timestamps, ticket_id, channel, confidence

## Phase 3: Retrieval API (Backend)

### 3.1 Semantic Search (pgvector)
- [ ] KNN top-K with tenant filter; optional type filters (tickets/logs/docs)
- [ ] Optional local cross-encoder reranker (MiniLM/BGE) with cutoff at top-5
- [ ] Search API endpoints with filters

### 3.2 Query Enhancement
- [ ] Synonym expansion for core incident terms (network/db/disk/auth/service)
- [ ] Time window/recency boost for recent items
- [ ] Query preprocessing and normalization

### 3.3 Response Format
- [ ] Return chunks + document metadata + citation anchors (line ranges/ids)
- [ ] Pagination support
- [ ] Response caching for common queries

## Phase 4: Runbook Generation/Update (Backend)

### 4.1 Templates and Rules
- [ ] Prompt templates per category (network, db, disk, auth, services)
- [ ] Output schema: title, prerequisites, steps, verification, rollback, references, risks
- [ ] Template management system

### 4.2 Create vs Update Logic
- [ ] Similarity threshold (e.g., >=0.85 on title/intent) → propose update (diff sections)
- [ ] Below threshold → create new runbook
- [ ] Versioning: store `body_md`, `metadata` (JSON), `confidence`, `parent_version_id`
- [ ] Audit trail: who/when/what changed (diff summary)

### 4.3 Confidence & Citations
- [ ] Confidence from retrieval coverage + LLM consistency checks
- [ ] Include citations (doc type, source, anchor) in runbook metadata
- [ ] Citation validation and link checking

## Phase 5: Webapp (MVP UI)

### 5.1 Auth + Tenant Context
- [ ] Email/password (local) with JWT; multi-tenant switcher
- [ ] User management and role-based access
- [ ] Session management and security

### 5.2 Ingestion UI
- [ ] File upload: Slack JSON, CSV (tickets), txt/md (logs/docs)
- [ ] Show parsed preview, mapped fields, errors
- [ ] Ingestion status & history (per file + per document)
- [ ] Progress indicators and error handling

### 5.3 Search & Runbooks
- [ ] Semantic search bar; filters (source type, date, confidence)
- [ ] Result list with citations; open in split view
- [ ] Generate runbook from query or from a specific ticket/log/doc
- [ ] View runbook, diff against previous version, approve update
- [ ] Export runbook (Markdown), copy-to-clipboard
- [ ] Runbook version history and comparison

### 5.4 Settings (MVP)
- [ ] Embedding model selection (predefined local)
- [ ] Chunking parameters (bounded, sane defaults)
- [ ] Tenant configuration
- [ ] System health monitoring

## Phase 6: QA & Ops (for POC)

### 6.1 Testing
- [ ] Seed datasets: small Slack JSON, ticket CSV, sample logs, kb md
- [ ] Unit tests: chunking/embedding, ingestion, search
- [ ] Integration tests: end-to-end ingestion→search→runbook
- [ ] Performance tests: large file handling, concurrent users

### 6.2 Monitoring & Logging
- [ ] Ingestion counts, chunk counts, search latency, runbook gen time
- [ ] Error tracking and alerting
- [ ] System health dashboard

### 6.3 Safety & Security
- [ ] Size limits on uploads; PII scrubbing toggles
- [ ] Input validation and sanitization
- [ ] Rate limiting and abuse prevention
- [ ] Data encryption at rest and in transit

## Phase 7: Production Readiness

### 7.1 Database Migration
- [ ] Export from Postgres: chunks, embeddings, metadata
- [ ] Import to Qdrant: bulk load with same IDs and payloads
- [ ] Switch provider: change VectorStore implementation via config
- [ ] Zero downtime migration strategy

### 7.2 Performance Optimization
- [ ] Embedding caching and batch processing
- [ ] Database query optimization
- [ ] Frontend performance (lazy loading, caching)
- [ ] CDN for static assets

### 7.3 Scalability
- [ ] Horizontal scaling for API servers
- [ ] Database connection pooling
- [ ] Load balancing and health checks
- [ ] Multi-region deployment support

## Done Criteria for MVP Phase

- [ ] Upload Slack JSON / tickets CSV / logs / docs and ingest successfully
- [ ] Search returns relevant chunks with citations (<3–5s end-to-end)
- [ ] Generate a runbook with structured steps and correct citations
- [ ] If same incident appears again, updates the existing runbook (versioned) rather than creating a duplicate
- [ ] All data stored in Postgres+pgvector; no external services required
- [ ] Web interface is functional and user-friendly
- [ ] Multi-tenant isolation works correctly
- [ ] System handles errors gracefully and provides clear feedback

## Success Metrics

- [ ] Ingestion success rate > 95%
- [ ] Search latency < 3 seconds
- [ ] Runbook generation time < 10 seconds
- [ ] User satisfaction score > 4.0/5.0
- [ ] System uptime > 99.5%
- [ ] Zero data loss incidents
- [ ] Successful runbook update rate > 90%

---

**Last Updated**: October 26, 2024
**Status**: Ready to begin Phase 1.1 - System Scaffolding

