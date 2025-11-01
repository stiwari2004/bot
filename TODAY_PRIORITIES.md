# Today's Priorities - RAG+LLM Knowledge Masterpiece

## 🎯 Goal
Build a robust, production-ready foundation for knowledge creation and autonomous agent evolution.

---

## 🚨 CRITICAL ISSUES TO FIX (Priority Order)

### 1. Switch from HuggingFace to Local LLM (URGENT)
**Problem**: Currently using DialoGPT which is wrong for structured tasks
**Impact**: Poor quality runbook generation

**Action**:
- [ ] Already using llama.cpp (llama3.1:8b) ✅ 
- [ ] Verify LLM service is correctly configured
- [ ] Test quality improvements
- [ ] Remove/replace HuggingFace fallbacks

**Time**: 30 min

---

### 2. Asynchronous I/O Blocking (HIGH)
**Problem**: Synchronous requests block async event loop
**Impact**: Reduced throughput, poor performance

**Files to Fix**:
- `backend/app/services/llm_service.py` - HuggingFaceLLMService
- `backend/app/services/embedding_service.py` - sentence-transformers

**Action**:
- [ ] Replace `requests.post` with `httpx.AsyncClient`
- [ ] Move embedding generation to `asyncio.to_thread`
- [ ] Add proper async/await patterns
- [ ] Performance testing

**Time**: 2-3 hours

---

### 3. Embedding Model Upgrade (HIGH)
**Problem**: all-MiniLM-L6-v2 is too small for quality search
**Impact**: Poor RAG retrieval, weak knowledge base

**Action**:
- [ ] Upgrade to `BAAI/bge-large-en-v1.5` (1024 dims)
- [ ] Update config.py
- [ ] Handle dimension change in database
- [ ] Create reindexing migration script
- [ ] Test search quality improvement

**Time**: 2-3 hours

---

### 4. Implement LLM Guardrails & YAML Validation (HIGH)
**Problem**: No schema validation, potential unsafe commands
**Impact**: Security risk, invalid runbooks

**Action**:
- [ ] Create Pydantic schema for Runbook YAML
- [ ] Add comprehensive validation
- [ ] Implement command allow-list
- [ ] Reject/flag unknown commands
- [ ] Add severity levels (safe/moderate/dangerous)

**Time**: 2-3 hours

---

### 5. Structured Logging (MEDIUM)
**Problem**: Print statements everywhere
**Impact**: Poor observability, hard to debug in production

**Action**:
- [ ] Setup Python logging with structured format
- [ ] Replace all print() with proper logging
- [ ] Add request IDs for tracing
- [ ] Configure JSON logs for ELK/Loki
- [ ] Add performance metrics

**Time**: 1-2 hours

---

### 6. Background Task Queue (MEDIUM)
**Problem**: Heavy tasks block requests
**Impact**: Timeouts, poor user experience

**Action**:
- [ ] Setup Celery or RQ
- [ ] Move embedding generation to background
- [ ] Move runbook generation to background
- [ ] Add job status endpoints
- [ ] Add progress tracking UI

**Time**: 3-4 hours

---

### 7. Hybrid Retrieval + Reranking (MEDIUM)
**Problem**: Only vector similarity, missing keyword search
**Impact**: Lower search precision

**Action**:
- [ ] Add Postgres full-text search
- [ ] Combine vector + keyword search
- [ ] Implement simple reranker
- [ ] A/B test hybrid approach
- [ ] Measure improvement

**Time**: 3-4 hours

---

### 8. Tenant Isolation Security (LOW but Important)
**Problem**: No DB-level row security
**Impact**: Potential data leakage

**Action**:
- [ ] Add Postgres RLS policies
- [ ] Test tenant isolation
- [ ] Add security audit

**Time**: 1-2 hours

---

## 🚀 KNOWLEDGE BASE ENHANCEMENTS

### 9. Bulk Knowledge Import (HIGH)
**Goal**: Enable mass ingestion of organizational knowledge

**Action**:
- [ ] CSV bulk upload endpoint
- [ ] Jira export parser
- [ ] ServiceNow CSV parser
- [ ] Slack export parser
- [ ] Batch processing with progress
- [ ] Deduplication logic
- [ ] Error recovery

**Time**: 3-4 hours

---

### 10. Advanced Search UI (MEDIUM)
**Goal**: Better user experience for knowledge discovery

**Action**:
- [ ] Add source type badges (doc/runbook)
- [ ] Add filters (by type, date, source)
- [ ] Add sorting options
- [ ] Highlight search terms
- [ ] Show confidence scores
- [ ] Add citation links

**Time**: 2-3 hours

---

### 11. Runbook Quality Improvements (HIGH)
**Goal**: Better, more reliable runbooks

**Action**:
- [ ] Enhanced confidence scoring
- [ ] Better citation tracking
- [ ] Multi-step validation
- [ ] Auto-flag low confidence
- [ ] Version comparison
- [ ] Quality metrics dashboard

**Time**: 2-3 hours

---

## 📅 TODAY'S EXECUTION PLAN

### Morning Session (9AM - 1PM): Critical Fixes
1. ✅ **30 min**: Verify llama.cpp setup
2. **2 hours**: Fix async I/O blocking
3. **30 min**: Coffee break ☕
4. **2 hours**: Upgrade embedding model + reindex
5. **30 min**: Test improvements

**Morning Goal**: Foundation is stable and fast

---

### Afternoon Session (2PM - 6PM): Knowledge Base
6. **2 hours**: LLM guardrails & validation
7. **1 hour**: Structured logging
8. **30 min**: Break
9. **2.5 hours**: Bulk knowledge import

**Afternoon Goal**: Robust knowledge ingestion

---

### Evening Session (7PM - 10PM): Polish
10. **1 hour**: Advanced search UI
11. **2 hours**: Background task queue setup

**Evening Goal**: Production-ready polish

---

## 🎯 SUCCESS CRITERIA

By end of today:
- ✅ No sync I/O blocking
- ✅ Better embedding model active
- ✅ Guardrails prevent unsafe commands
- ✅ Structured logging in place
- ✅ Bulk import working
- ✅ Search quality improved
- ✅ Background jobs implemented

---

## 💡 KEY DECISIONS NEEDED

1. **Task Queue**: Celery vs RQ vs FastAPI BackgroundTasks?
2. **Reranking**: Build custom or use off-the-shelf?
3. **Monitoring**: Which tooling? (Prometheus, Loki, custom)
4. **Batch Size**: How many docs to process at once?

---

## 📊 METRICS TO TRACK

- Search precision improvement (before/after embedding upgrade)
- Async performance gains
- Validation rejections
- Bulk import throughput
- Background job success rate
- Search latency

---

Let's build something amazing today! 🚀

