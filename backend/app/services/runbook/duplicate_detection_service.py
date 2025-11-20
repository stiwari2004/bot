"""
Service for detecting duplicate runbooks
"""
import json
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.runbook import Runbook
from app.core.logging import get_logger

logger = get_logger(__name__)


class DuplicateDetectionService:
    """Service for detecting duplicate runbooks"""
    
    def check_duplicate(
        self,
        db: Session,
        issue_description: str,
        tenant_id: int
    ) -> Tuple[bool, Optional[Runbook]]:
        """
        Check if a runbook already exists for the given issue description.
        Returns (is_duplicate, existing_runbook)
        """
        try:
            # Normalize issue description for comparison
            normalized_issue = issue_description.lower().strip()
            
            # Extract core issue (first sentence, remove common words)
            core_issue_parts = []
            for word in normalized_issue.split():
                # Remove common stop words
                if word not in ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'on', 'in', 'at', 'to', 'for', 'of', 'with']:
                    core_issue_parts.append(word)
            core_issue = ' '.join(core_issue_parts[:10])  # First 10 meaningful words
            
            # Get all active runbooks for this tenant (exclude archived)
            existing_runbooks = db.query(Runbook).filter(
                Runbook.tenant_id == tenant_id,
                Runbook.is_active == "active"
            ).all()
            
            logger.info(f"Checking {len(existing_runbooks)} existing runbooks for duplicates...")
            
            for existing_rb in existing_runbooks:
                if not existing_rb.meta_data:
                    continue
                    
                try:
                    meta = json.loads(existing_rb.meta_data) if isinstance(existing_rb.meta_data, str) else existing_rb.meta_data
                    
                    # Check issue_description in meta_data (primary check)
                    existing_issue = meta.get('issue_description', '').lower().strip()
                    
                    # Check description in runbook_spec (secondary check - this is where LLM puts the issue)
                    runbook_spec = meta.get('runbook_spec', {})
                    existing_description = runbook_spec.get('description', '').lower().strip()
                    
                    # Extract core from existing description
                    existing_core = None
                    if existing_description:
                        # Remove common suffix patterns
                        for suffix in ['this issue requires', 'requires immediate attention', 'to prevent service disruption', 'and data loss']:
                            if suffix in existing_description:
                                existing_description = existing_description.split(suffix)[0].strip()
                        
                        # Extract core words from existing description
                        existing_core_parts = []
                        for word in existing_description.split():
                            if word not in ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'on', 'in', 'at', 'to', 'for', 'of', 'with']:
                                existing_core_parts.append(word)
                        existing_core = ' '.join(existing_core_parts[:10])
                    
                    # Check for duplicate
                    is_duplicate = False
                    
                    # Method 1: Check against issue_description
                    if existing_issue:
                        existing_issue_normalized = existing_issue.lower().strip()
                        # Check if core issues match (first 10 meaningful words)
                        if core_issue and existing_core:
                            # Calculate word overlap
                            core_words = set(core_issue.split())
                            existing_words = set(existing_core.split())
                            if len(core_words) > 0:
                                overlap = len(core_words & existing_words) / len(core_words)
                                if overlap >= 0.6:  # 60% word overlap
                                    is_duplicate = True
                                    logger.info(f"Duplicate detected: {overlap:.1%} word overlap with runbook {existing_rb.id}")
                        
                        # Also check substring matches
                        if not is_duplicate:
                            if (normalized_issue in existing_issue_normalized or 
                                existing_issue_normalized in normalized_issue or
                                core_issue in existing_issue_normalized or
                                existing_issue_normalized in core_issue):
                                is_duplicate = True
                                logger.info(f"Duplicate detected: substring match with runbook {existing_rb.id}")
                    
                    # Method 2: Check against runbook description (where LLM stores the issue)
                    if not is_duplicate and existing_description:
                        # Check word overlap
                        if core_issue and existing_core:
                            core_words = set(core_issue.split())
                            existing_words = set(existing_core.split())
                            if len(core_words) > 0:
                                overlap = len(core_words & existing_words) / len(core_words)
                                if overlap >= 0.6:  # 60% word overlap
                                    is_duplicate = True
                                    logger.info(f"Duplicate detected: {overlap:.1%} word overlap with runbook {existing_rb.id} description")
                        
                        # Also check substring matches
                        if not is_duplicate:
                            if (core_issue in existing_description or 
                                existing_description.startswith(core_issue) or
                                normalized_issue in existing_description):
                                is_duplicate = True
                                logger.info(f"Duplicate detected: substring match with runbook {existing_rb.id} description")
                    
                    if is_duplicate:
                        logger.warning(
                            f"Duplicate runbook detected: "
                            f"existing ID {existing_rb.id}, title: {existing_rb.title}"
                        )
                        return (True, existing_rb)
                        
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    logger.debug(f"Error checking duplicate for runbook {existing_rb.id}: {e}")
                    continue
                    
            return (False, None)
            
        except Exception as e:
            # If duplicate check fails, log but don't block generation
            logger.warning(f"Failed to check for duplicate runbooks: {e}. Continuing with generation.")
            return (False, None)

