"""
Self-learning service for input extraction
Matches user input back to metadata to learn where inputs should be extracted from
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.runbook import Runbook
from app.core.logging import get_logger
import json
from datetime import datetime

logger = get_logger(__name__)


class InputLearningService:
    """
    Self-learning service that:
    1. Matches user input back to metadata
    2. Identifies where it should have been extracted
    3. Flags for metadata mapping updates
    4. Stores learned mappings
    """
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def learn_from_user_input(
        self,
        ticket: Ticket,
        user_inputs: Dict[str, Any],
        runbook: Runbook,
    ) -> Dict[str, Any]:
        """
        Learn from user input by matching it back to metadata.
        
        Args:
            ticket: Ticket object
            user_inputs: Dictionary of user-provided input values
            runbook: Runbook object
            
        Returns:
            {
                "learned_mappings": [...],  # New mappings discovered
                "flags": [...],             # Flags for manual review
                "confidence": {...},        # Confidence in learned mappings
                "total_learned": int        # Number of mappings learned
            }
        """
        learned_mappings = []
        flags = []
        
        meta = ticket.meta_data or {}
        raw = ticket.raw_payload or {}
        
        # For each user input, try to find it in metadata
        for input_name, user_value in user_inputs.items():
            if not user_value or not isinstance(user_value, str):
                continue
            
            # Search metadata for this value
            found_location = self._find_in_metadata(
                user_value,
                ticket.source,
                meta,
                raw
            )
            
            if found_location:
                # We found where it should have been extracted!
                mapping = {
                    "input_name": input_name,
                    "source": ticket.source,
                    "metadata_path": found_location["path"],
                    "metadata_value": found_location["value"],
                    "user_value": user_value,
                    "confidence": found_location["confidence"],
                    "ticket_id": ticket.id,
                    "runbook_id": runbook.id,
                    "learned_at": datetime.utcnow().isoformat()
                }
                
                learned_mappings.append(mapping)
                
                # Store the mapping for future use
                self._store_mapping(mapping, ticket.tenant_id)
                
                # Flag if confidence is low (needs manual review)
                if found_location["confidence"] < 0.8:
                    flags.append({
                        "input_name": input_name,
                        "suggested_path": found_location["path"],
                        "reason": "Low confidence match - needs review",
                        "ticket_id": ticket.id,
                        "confidence": found_location["confidence"]
                    })
        
        logger.info(
            f"Learning complete for ticket {ticket.id}: "
            f"{len(learned_mappings)} mappings learned, {len(flags)} flags created"
        )
        
        return {
            "learned_mappings": learned_mappings,
            "flags": flags,
            "total_learned": len(learned_mappings)
        }
    
    def _find_in_metadata(
        self,
        user_value: str,
        source: str,
        meta: Dict,
        raw: Dict
    ) -> Optional[Dict]:
        """Find user value in metadata and return location"""
        
        # Normalize user value for comparison
        normalized_user = user_value.lower().strip()
        
        # Search strategy based on source
        if source == "datadog":
            return self._find_in_datadog(normalized_user, meta, raw)
        elif source == "servicenow":
            return self._find_in_servicenow(normalized_user, meta, raw)
        
        # Generic search for unknown sources
        return self._find_generic(normalized_user, meta, raw)
    
    def _find_in_datadog(self, user_value: str, meta: Dict, raw: Dict) -> Optional[Dict]:
        """Find value in Datadog metadata"""
        
        # Check tags
        tags = raw.get("tags", []) or meta.get("tags", [])
        for tag in tags:
            if isinstance(tag, str) and ":" in tag:
                key, value = tag.split(":", 1)
                value_lower = value.lower().strip()
                if user_value in value_lower or value_lower in user_value:
                    return {
                        "path": f"tags.{key}",
                        "value": value,
                        "confidence": 0.9 if user_value == value_lower else 0.7
                    }
            elif isinstance(tag, dict):
                for k, v in tag.items():
                    if isinstance(v, str) and user_value in v.lower():
                        return {
                            "path": f"tags.{k}",
                            "value": v,
                            "confidence": 0.8
                        }
        
        # Check host
        host = raw.get("host") or meta.get("host")
        if host and user_value in host.lower():
            return {
                "path": "host",
                "value": host,
                "confidence": 0.95 if user_value == host.lower() else 0.8
            }
        
        # Check service
        service = raw.get("service") or meta.get("service")
        if service and user_value in service.lower():
            return {
                "path": "service",
                "value": service,
                "confidence": 0.9
            }
        
        return None
    
    def _find_in_servicenow(self, user_value: str, meta: Dict, raw: Dict) -> Optional[Dict]:
        """Find value in ServiceNow metadata"""
        
        # Check CI fields
        ci = raw.get("configuration_item") or meta.get("ci") or raw.get("cmdb_ci")
        if ci:
            if isinstance(ci, dict):
                for field, value in ci.items():
                    if value and isinstance(value, str) and user_value in value.lower():
                        return {
                            "path": f"configuration_item.{field}",
                            "value": value,
                            "confidence": 0.9
                        }
            elif isinstance(ci, str) and user_value in ci.lower():
                return {
                    "path": "configuration_item",
                    "value": ci,
                    "confidence": 0.85
                }
        
        # Check all custom fields (u_*)
        for key, value in raw.items():
            if key.startswith("u_") and value:
                if isinstance(value, str) and user_value in value.lower():
                    return {
                        "path": key,
                        "value": value,
                        "confidence": 0.8
                    }
        
        # Check metadata fields
        for key, value in meta.items():
            if value and isinstance(value, str) and user_value in value.lower():
                return {
                    "path": key,
                    "value": value,
                    "confidence": 0.75
                }
        
        return None
    
    def _find_generic(self, user_value: str, meta: Dict, raw: Dict) -> Optional[Dict]:
        """Generic search across all metadata fields"""
        # Search raw payload
        for key, value in raw.items():
            if value and isinstance(value, str) and user_value in value.lower():
                return {
                    "path": key,
                    "value": value,
                    "confidence": 0.7
                }
        
        # Search metadata
        for key, value in meta.items():
            if value and isinstance(value, str) and user_value in value.lower():
                return {
                    "path": key,
                    "value": value,
                    "confidence": 0.65
                }
        
        return None
    
    def _store_mapping(self, mapping: Dict[str, Any], tenant_id: int):
        """Store learned mapping in database"""
        try:
            from app.models.metadata_mapping import MetadataMapping
            
            # Check if mapping already exists for this tenant
            existing = self.db.query(MetadataMapping).filter(
                MetadataMapping.tenant_id == tenant_id,
                MetadataMapping.input_name == mapping["input_name"],
                MetadataMapping.source == mapping["source"],
                MetadataMapping.metadata_path == mapping["metadata_path"],
                MetadataMapping.is_active == True
            ).first()
            
            if existing:
                # Update usage count and confidence
                existing.usage_count += 1
                existing.last_used_at = datetime.utcnow()
                # Update confidence if new one is higher
                if mapping["confidence"] > existing.confidence:
                    existing.confidence = mapping["confidence"]
                self.db.commit()
                logger.debug(f"Updated existing mapping: {mapping['input_name']} -> {mapping['metadata_path']}")
            else:
                # Create new mapping
                new_mapping = MetadataMapping(
                    tenant_id=tenant_id,  # Get from ticket context
                    input_name=mapping["input_name"],
                    source=mapping["source"],
                    metadata_path=mapping["metadata_path"],
                    confidence=mapping["confidence"],
                    usage_count=1,
                    last_used_at=datetime.utcnow(),
                    is_active=True
                )
                self.db.add(new_mapping)
                self.db.commit()
                logger.info(f"Created new mapping: {mapping['input_name']} -> {mapping['metadata_path']}")
        except Exception as e:
            logger.error(f"Failed to store mapping: {e}")
            self.db.rollback()

