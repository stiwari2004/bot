"""
Runbook indexer for search functionality
"""
import json
import hashlib
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.runbook import Runbook
from app.schemas.runbook import RunbookResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class RunbookIndexer:
    """Handles runbook indexing for search"""
    
    def __init__(self, vector_service=None):
        self._vector_service = vector_service
    
    @property
    def vector_service(self):
        """Lazy property to create VectorStoreService only when needed"""
        if self._vector_service is None:
            from app.services.vector_store import VectorStoreService
            self._vector_service = VectorStoreService()
        return self._vector_service
    
    async def approve_and_index_runbook(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session
    ) -> RunbookResponse:
        """
        Approve a draft runbook and index it for search.
        This method updates the status to 'approved' and indexes it in the vector store.
        """
        try:
            # Get the runbook
            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id
            ).first()
            
            if not runbook:
                raise HTTPException(status_code=404, detail="Runbook not found")
            
            # Update status to approved
            runbook.status = 'approved'
            db.commit()
            db.refresh(runbook)
            
            logger.info(f"Runbook {runbook_id} approved, now indexing for search")
            
            # Index the runbook for search
            # Temporarily disabled indexing to avoid blocking on embedding model load
            # TODO: Re-enable when embedding model loading is made non-blocking
            # await self.index_runbook_for_search(runbook, db)
            logger.info(f"Runbook {runbook.id} created (indexing disabled to avoid blocking)")
            
            return RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=runbook.confidence,
                meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
                status=runbook.status,
                created_at=runbook.created_at,
                updated_at=runbook.updated_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error approving runbook {runbook_id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to approve runbook: {str(e)}")
    
    async def index_runbook_for_search(self, runbook: Runbook, db: Session) -> None:
        """
        Index an approved runbook in the vector store for searchability.
        Creates a document entry and chunks the runbook content.
        """
        try:
            from app.models.document import Document
            from app.services.ingestion import IngestionService
            
            # Build searchable text from runbook
            searchable_text = self.build_runbook_searchable_text(runbook)
            
            if not searchable_text:
                logger.warning(f"Cannot build searchable text for runbook {runbook.id}")
                return
            
            # Prepare metadata and hash
            content_hash = hashlib.sha256(searchable_text.encode()).hexdigest()
            
            metadata = json.dumps({
                "runbook_id": runbook.id,
                "source_type": "runbook",
                "title": runbook.title
            })
            
            # Check if already indexed for this specific runbook
            runbook_path = f"runbook_{runbook.id}.md"
            existing_doc = db.query(Document).filter(
                Document.path == runbook_path,
                Document.tenant_id == runbook.tenant_id
            ).first()
            
            if existing_doc:
                logger.info(f"Runbook {runbook.id} already indexed as document {existing_doc.id}")
                # Delete old chunks to re-chunk with new metadata
                from app.models.chunk import Chunk
                from app.models.embedding import Embedding
                db.query(Embedding).filter(Embedding.chunk_id.in_(
                    db.query(Chunk.id).filter(Chunk.document_id == existing_doc.id)
                )).delete(synchronize_session=False)
                db.query(Chunk).filter(Chunk.document_id == existing_doc.id).delete(synchronize_session=False)
                db.commit()
                document = existing_doc
            else:
                # Create new document
                document = Document(
                    tenant_id=runbook.tenant_id,
                    source_type='runbook',
                    title=f"Runbook: {runbook.title}",
                    path=runbook_path,
                    content=searchable_text,
                    content_hash=content_hash,
                    meta_data=metadata
                )
                
                db.add(document)
                db.commit()
                db.refresh(document)
                
                logger.info(f"Created document {document.id} for runbook {runbook.id}")
            
            # Chunk the content using ingestion service
            ingestion_service = IngestionService()
            chunks = await ingestion_service._create_chunks(document.id, searchable_text)
            
            # Create ChunkData objects for vector store
            chunk_data_objects = []
            for chunk_data in chunks:
                from app.core.vector_store import ChunkData
                # Add runbook_id to chunk metadata for easy extraction in search
                chunk_meta = chunk_data.get("metadata", {})
                chunk_meta["runbook_id"] = runbook.id
                chunk_data_objects.append(ChunkData(
                    document_id=document.id,
                    text=chunk_data["text"],
                    meta_data=chunk_meta
                ))
            
            # Upsert chunks with embeddings
            await self.vector_service.upsert_chunks(chunk_data_objects, db)
            
            logger.info(f"Successfully indexed runbook {runbook.id} with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error indexing runbook {runbook.id} for search: {e}")
            db.rollback()
    
    def build_runbook_searchable_text(self, runbook: Runbook) -> str:
        """Build comprehensive searchable text from runbook"""
        try:
            # Parse metadata
            metadata = json.loads(runbook.meta_data) if runbook.meta_data else {}
            runbook_spec = metadata.get('runbook_spec', {})
            
            # Build searchable text
            parts = []
            
            # Title
            parts.append(f"Title: {runbook.title}")
            
            # Issue description
            issue_desc = metadata.get('issue_description', '')
            if issue_desc:
                parts.append(f"Issue: {issue_desc}")
            
            # Runbook spec details
            if runbook_spec:
                if runbook_spec.get('description'):
                    parts.append(f"Description: {runbook_spec['description']}")
                if runbook_spec.get('service'):
                    parts.append(f"Service Type: {runbook_spec['service']}")
                
                # Add all steps
                steps = runbook_spec.get('steps', [])
                for step in steps:
                    if isinstance(step, dict):
                        if step.get('name'):
                            parts.append(f"Step: {step['name']}")
                        if step.get('description'):
                            parts.append(step['description'])
                        if step.get('command'):
                            parts.append(f"Command: {step['command']}")
                
                # Add prechecks
                prechecks = runbook_spec.get('prechecks', [])
                for check in prechecks:
                    if isinstance(check, dict):
                        if check.get('description'):
                            parts.append(f"Precheck: {check['description']}")
                        if check.get('command'):
                            parts.append(f"Precheck Command: {check['command']}")
                
                # Add postchecks
                postchecks = runbook_spec.get('postchecks', [])
                for check in postchecks:
                    if isinstance(check, dict):
                        if check.get('description'):
                            parts.append(f"Postcheck: {check['description']}")
                        if check.get('command'):
                            parts.append(f"Postcheck Command: {check['command']}")
            
            return "\n\n".join(parts)
            
        except Exception as e:
            logger.error(f"Error building searchable text for runbook {runbook.id}: {e}")
            return ""




