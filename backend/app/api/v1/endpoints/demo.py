"""
Demo endpoints for testing the system
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import json
import hashlib

from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.ingestion import IngestionService
from app.services.vector_store import VectorStoreService
from app.core.vector_store import ChunkData

router = APIRouter()


@router.post("/upload-demo")
async def upload_demo_file(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process a demo file"""
    try:
        ingestion_service = IngestionService()
        
        # Process the file (using tenant_id = 1 for demo)
        result = await ingestion_service.process_file(
            file=file,
            source_type=source_type,
            title=title or file.filename,
            tenant_id=1,  # Demo tenant
            db=db
        )
        
        return {
            "message": "File uploaded and processed successfully",
            "document_id": result["document_id"],
            "chunks_created": result["chunks_created"],
            "source_type": source_type,
            "filename": file.filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/search-demo")
async def search_demo(
    query: str = Form(...),
    db: Session = Depends(get_db)
):
    """Demo semantic search"""
    try:
        vector_service = VectorStoreService()
        
        # Perform hybrid search (using tenant_id = 1 for demo)
        results = await vector_service.hybrid_search(
            query=query,
            tenant_id=1,  # Demo tenant
            db=db,
            top_k=5,
            use_reranking=True
        )
        
        # Format results for display
        formatted_results = []
        for result in results:
            formatted_result = {
                "text": result.text[:200] + "..." if len(result.text) > 200 else result.text,
                "score": round(result.score, 3),
                "source": result.document_source,
                "title": result.document_title
            }
            # Add runbook_id if available in metadata
            if result.meta_data and "runbook_id" in result.meta_data:
                formatted_result["runbook_id"] = result.meta_data["runbook_id"]
            formatted_results.append(formatted_result)
        
        return {
            "query": query,
            "results_count": len(results),
            "results": formatted_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/create-sample-data")
async def create_sample_data(
    db: Session = Depends(get_db)
):
    """Create sample data for testing"""
    try:
        vector_service = VectorStoreService()
        ingestion_service = IngestionService()
        
        # Create sample documents and chunks
        sample_data = [
            {
                "title": "Network Troubleshooting Guide",
                "content": "When network connectivity issues occur, first check the physical connections. Verify that all cables are properly connected and that network interface cards are functioning. Common issues include loose cables, faulty switches, or incorrect IP configurations. Use ping and traceroute commands to diagnose connectivity problems.",
                "source_type": "doc"
            },
            {
                "title": "Database Connection Error",
                "content": "Database connection failures are often caused by incorrect connection strings, network issues, or database server problems. Check the database server status, verify connection parameters, and ensure proper authentication credentials. Common solutions include restarting the database service, checking firewall settings, and validating connection pool configurations.",
                "source_type": "ticket"
            },
            {
                "title": "Server Performance Issues",
                "content": "High CPU usage and memory consumption can cause server performance degradation. Monitor system resources using top, htop, or performance monitoring tools. Identify processes consuming excessive resources and optimize application code. Consider scaling resources or implementing caching strategies to improve performance.",
                "source_type": "log"
            }
        ]
        
        total_chunks = 0
        for data in sample_data:
            # Create document
            from app.models.document import Document
            document = Document(
                tenant_id=1,  # Demo tenant
                source_type=data["source_type"],
                title=data["title"],
                content=data["content"],
                content_hash=hashlib.sha256(data["content"].encode()).hexdigest(),
                meta_data=json.dumps({"created_by": "demo", "type": "sample"})
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Create chunks
            chunks = await ingestion_service._create_chunks(document.id, data["content"])
            chunk_data_objects = []
            for chunk_data in chunks:
                chunk_data_objects.append(ChunkData(
                    document_id=document.id,
                    text=chunk_data["text"],
                    meta_data=chunk_data["metadata"]
                ))
            
            # Upsert chunks with embeddings
            await vector_service.upsert_chunks(chunk_data_objects, db)
            total_chunks += len(chunks)
        
        return {
            "message": "Sample data created successfully",
            "documents_created": len(sample_data),
            "total_chunks": total_chunks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sample data creation failed: {str(e)}")


@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db)
):
    """Get system statistics"""
    try:
        from app.models.document import Document
        from app.models.chunk import Chunk
        from app.models.runbook import Runbook
        
        # Count documents and chunks (using tenant_id = 1 for demo)
        doc_count = db.query(Document).filter(Document.tenant_id == 1).count()
        chunk_count = db.query(Chunk).join(Document).filter(Document.tenant_id == 1).count()
        runbook_count = db.query(Runbook).filter(
            Runbook.tenant_id == 1,
            Runbook.is_active == "active"
        ).count()
        
        # Count by source type
        source_stats = {}
        for source_type in ["slack", "ticket", "log", "doc"]:
            count = db.query(Document).filter(
                Document.tenant_id == 1,  # Demo tenant
                Document.source_type == source_type
            ).count()
            source_stats[source_type] = count
        
        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "total_runbooks": runbook_count,
            "by_source_type": source_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")
