"""
File ingestion service
"""
from typing import Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session
import hashlib
import json
import os
import csv
import io

from app.models.document import Document
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.vector_store import VectorStoreService
from app.core.vector_store import ChunkData


class IngestionService:
    """Service for ingesting files and creating knowledge base"""
    
    def __init__(self):
        self.vector_service = VectorStoreService()
    
    async def process_file(
        self,
        file: UploadFile,
        source_type: str,
        title: str,
        tenant_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Process uploaded file and create document with chunks"""
        
        # Read file content
        content = await file.read()
        # Try UTF-8 first, fallback to latin-1 for CSV files
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content_str = content.decode('latin-1')
            except UnicodeDecodeError:
                content_str = content.decode('utf-8', errors='ignore')
        
        # Calculate content hash
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        
        # Check if document already exists
        existing_doc = db.query(Document).filter(
            Document.content_hash == content_hash,
            Document.tenant_id == tenant_id
        ).first()
        
        if existing_doc:
            return {
                "document_id": existing_doc.id,
                "chunks_created": 0,
                "message": "Document already exists"
            }
        
        # Parse content based on source type
        parsed_content = await self._parse_content(content_str, source_type)
        
        # Create document
        document = Document(
            tenant_id=tenant_id,
            source_type=source_type,
            title=title,
            path=file.filename,
            content=parsed_content["content"],
            content_hash=content_hash,
            metadata=json.dumps(parsed_content["metadata"])
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Create chunks
        chunks = await self._create_chunks(document.id, parsed_content["content"])
        
        # Convert to ChunkData objects for vector store
        chunk_data_objects = []
        for chunk_data in chunks:
            chunk_data_objects.append(ChunkData(
                document_id=document.id,
                text=chunk_data["text"],
                meta_data=chunk_data["metadata"]
            ))
        
        # Upsert chunks with embeddings using vector store
        await self.vector_service.upsert_chunks(chunk_data_objects, db)
        
        return {
            "document_id": document.id,
            "chunks_created": len(chunks),
            "message": "Document processed successfully"
        }
    
    async def _parse_content(self, content: str, source_type: str) -> Dict[str, Any]:
        """Parse content based on source type"""
        if source_type == "slack":
            return await self._parse_slack(content)
        elif source_type == "ticket":
            return await self._parse_ticket(content)
        elif source_type == "jira":
            return await self._parse_jira(content)
        elif source_type == "servicenow":
            return await self._parse_servicenow(content)
        elif source_type == "log":
            return await self._parse_log(content)
        elif source_type == "doc":
            return await self._parse_document(content)
        else:
            return {
                "content": content,
                "metadata": {"source_type": source_type}
            }
    
    async def _parse_slack(self, content: str) -> Dict[str, Any]:
        """Parse Slack JSON export"""
        try:
            data = json.loads(content)
            # Extract messages and threads
            messages = []
            for message in data.get("messages", []):
                messages.append({
                    "text": message.get("text", ""),
                    "user": message.get("user", ""),
                    "timestamp": message.get("ts", ""),
                    "thread_ts": message.get("thread_ts")
                })
            
            return {
                "content": "\n".join([msg["text"] for msg in messages]),
                "metadata": {
                    "source_type": "slack",
                    "message_count": len(messages),
                    "channels": data.get("channels", [])
                }
            }
        except json.JSONDecodeError:
            return {
                "content": content,
                "metadata": {"source_type": "slack", "error": "Invalid JSON"}
            }
    
    async def _parse_ticket(self, content: str) -> Dict[str, Any]:
        """Parse ticket CSV with proper CSV handling"""
        try:
            # Use csv module for proper parsing
            reader = csv.DictReader(io.StringIO(content))
            tickets = list(reader)
            
            # Build content from tickets
            ticket_texts = []
            for ticket in tickets:
                # Prioritize common ticket fields
                ticket_id = ticket.get('id') or ticket.get('ticket_id') or ticket.get('number', '')
                description = ticket.get('description') or ticket.get('summary') or ticket.get('title', '')
                status = ticket.get('status') or ticket.get('state', '')
                priority = ticket.get('priority', '')
                
                ticket_texts.append(f"Ticket {ticket_id} [{status}/{priority}]: {description}")
            
            return {
                "content": "\n".join(ticket_texts),
                "metadata": {
                    "source_type": "ticket",
                    "ticket_count": len(tickets),
                    "headers": list(tickets[0].keys()) if tickets else []
                }
            }
        except Exception as e:
            # Fallback to simple parsing
            return {
                "content": content,
                "metadata": {"source_type": "ticket", "error": str(e)}
            }
    
    async def _parse_jira(self, content: str) -> Dict[str, Any]:
        """Parse Jira JSON export or CSV"""
        try:
            # Try JSON first (Jira API export)
            data = json.loads(content)
            if isinstance(data, dict) and "issues" in data:
                issues = data["issues"]
            elif isinstance(data, list):
                issues = data
            else:
                issues = []
            
            issue_texts = []
            for issue in issues:
                key = issue.get("key", "")
                summary = issue.get("fields", {}).get("summary", "")
                description = issue.get("fields", {}).get("description", "")
                status = issue.get("fields", {}).get("status", {}).get("name", "")
                priority = issue.get("fields", {}).get("priority", {}).get("name", "")
                
                issue_texts.append(f"Jira {key} [{status}/{priority}]: {summary}. {description}")
            
            return {
                "content": "\n".join(issue_texts),
                "metadata": {
                    "source_type": "jira",
                    "issue_count": len(issues)
                }
            }
        except json.JSONDecodeError:
            # Fall back to CSV parsing
            return await self._parse_ticket(content)
    
    async def _parse_servicenow(self, content: str) -> Dict[str, Any]:
        """Parse ServiceNow CSV export"""
        try:
            reader = csv.DictReader(io.StringIO(content))
            tickets = list(reader)
            
            ticket_texts = []
            for ticket in tickets:
                number = ticket.get('number') or ticket.get('sys_id', '')
                short_description = ticket.get('short_description') or ticket.get('description', '')
                state = ticket.get('state') or ticket.get('work_notes', '')
                priority = ticket.get('priority', '')
                
                ticket_texts.append(f"ServiceNow {number} [{state}/{priority}]: {short_description}")
            
            return {
                "content": "\n".join(ticket_texts),
                "metadata": {
                    "source_type": "servicenow",
                    "ticket_count": len(tickets)
                }
            }
        except Exception as e:
            return {
                "content": content,
                "metadata": {"source_type": "servicenow", "error": str(e)}
            }

    async def _parse_log(self, content: str) -> Dict[str, Any]:
        """Parse log file"""
        lines = content.split('\n')
        error_lines = [line for line in lines if any(keyword in line.upper() for keyword in ['ERROR', 'WARN', 'CRITICAL', 'FATAL'])]
        
        return {
            "content": content,
            "metadata": {
                "source_type": "log",
                "total_lines": len(lines),
                "error_lines": len(error_lines)
            }
        }
    
    async def _parse_document(self, content: str) -> Dict[str, Any]:
        """Parse markdown/document"""
        return {
            "content": content,
            "metadata": {
                "source_type": "doc",
                "word_count": len(content.split())
            }
        }
    
    async def _create_chunks(self, document_id: int, content: str) -> list:
        """Create text chunks from content using sentence-aware chunking"""
        from app.core.config import settings
        import re
        
        # Split content into sentences for better chunking
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        chunks = []
        current_chunk = ""
        chunk_size = settings.CHUNK_SIZE * 4  # Approximate characters
        overlap = settings.CHUNK_OVERLAP * 4
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size, save current chunk
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "hash": hashlib.sha256(current_chunk.strip().encode()).hexdigest(),
                    "metadata": {
                        "chunk_type": "sentence_based",
                        "length": len(current_chunk.strip())
                    }
                })
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "hash": hashlib.sha256(current_chunk.strip().encode()).hexdigest(),
                "metadata": {
                    "chunk_type": "sentence_based",
                    "length": len(current_chunk.strip())
                }
            })
        
        return chunks
    

