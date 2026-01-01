"""
Runbook Promotion Service
Handles promotion of runbooks from dev to production environment
"""
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.runbook import Runbook
from app.models.deployment_approval import DeploymentApproval
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
import yaml

logger = get_logger(__name__)


class RunbookPromotionService:
    """Service for promoting runbooks from dev to production"""
    
    def validate_runbook_for_promotion(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int
    ) -> tuple[bool, Optional[str]]:
        """
        Validate runbook before promotion
        
        Args:
            db: Database session
            runbook_id: Runbook ID to validate
            tenant_id: Tenant ID
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id,
                Runbook.environment == "dev"
            ).first()
            
            if not runbook:
                return False, "Runbook not found or not in dev environment"
            
            # Check status
            if runbook.status != "approved":
                return False, f"Runbook must be approved before promotion. Current status: {runbook.status}"
            
            # Validate runbook content
            if not runbook.body_md or not runbook.body_md.strip():
                return False, "Runbook body is empty"
            
            # Try to parse YAML from body_md
            try:
                # Extract YAML from markdown code fence if present
                body_content = runbook.body_md
                if "```yaml" in body_content:
                    yaml_start = body_content.find("```yaml") + 7
                    yaml_end = body_content.find("```", yaml_start)
                    if yaml_end > yaml_start:
                        body_content = body_content[yaml_start:yaml_end].strip()
                elif "```" in body_content:
                    # Try generic code fence
                    code_start = body_content.find("```") + 3
                    code_end = body_content.find("```", code_start)
                    if code_end > code_start:
                        body_content = body_content[code_start:code_end].strip()
                
                # Parse YAML
                parsed = yaml.safe_load(body_content)
                if not parsed:
                    return False, "Runbook YAML is empty or invalid"
                
                # Validate required fields
                if "title" not in parsed:
                    return False, "Runbook YAML missing required field: title"
                
                if "main_steps" not in parsed and "prechecks" not in parsed:
                    return False, "Runbook YAML must contain at least main_steps or prechecks"
                
            except yaml.YAMLError as e:
                return False, f"Invalid YAML format: {str(e)}"
            except Exception as e:
                logger.warning(f"Error validating runbook YAML: {e}")
                # Don't fail on YAML parsing if it's not critical
                pass
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating runbook {runbook_id}: {e}", exc_info=True)
            return False, f"Validation error: {str(e)}"
    
    def promote_runbook(
        self,
        db: Session,
        dev_runbook_id: int,
        tenant_id: int,
        approved_by: int,
        dry_run: bool = False
    ) -> tuple[Optional[Runbook], Optional[str]]:
        """
        Promote a runbook from dev to production
        
        Args:
            db: Database session
            dev_runbook_id: ID of dev runbook to promote
            tenant_id: Tenant ID
            approved_by: User ID who approved the promotion
            dry_run: If True, validate but don't create production runbook
            
        Returns:
            Tuple of (production_runbook, error_message)
        """
        try:
            # Get dev runbook
            dev_runbook = db.query(Runbook).filter(
                Runbook.id == dev_runbook_id,
                Runbook.tenant_id == tenant_id,
                Runbook.environment == "dev"
            ).first()
            
            if not dev_runbook:
                return None, "Dev runbook not found"
            
            # Validate before promotion
            is_valid, error_msg = self.validate_runbook_for_promotion(db, dev_runbook_id, tenant_id)
            if not is_valid:
                return None, error_msg
            
            if dry_run:
                logger.info(f"Dry run: Runbook {dev_runbook_id} is valid for promotion")
                return None, None
            
            # Check if already promoted
            existing_prod = db.query(Runbook).filter(
                Runbook.promoted_from_id == dev_runbook_id,
                Runbook.environment == "production",
                Runbook.tenant_id == tenant_id
            ).first()
            
            if existing_prod:
                logger.info(f"Runbook {dev_runbook_id} already promoted as {existing_prod.id}")
                return existing_prod, None
            
            # Create production runbook
            prod_runbook = Runbook(
                tenant_id=tenant_id,
                title=dev_runbook.title,
                body_md=dev_runbook.body_md,
                meta_data=dev_runbook.meta_data,
                confidence=dev_runbook.confidence,
                parent_version_id=dev_runbook.parent_version_id,
                status="approved",  # Production runbooks are auto-approved
                is_active="active",
                environment="production",
                promoted_from_id=dev_runbook_id,
                promoted_at=datetime.now(timezone.utc)
            )
            
            db.add(prod_runbook)
            db.commit()
            db.refresh(prod_runbook)
            
            # Create deployment approval record
            approval = DeploymentApproval(
                deployment_type="runbook",
                target_environment="production",
                reference_id=prod_runbook.id,
                reference_name=dev_runbook.title,
                status="deployed",
                requested_by=approved_by,
                approved_by=approved_by,
                approved_at=datetime.now(timezone.utc),
                deployed_at=datetime.now(timezone.utc),
                metadata={
                    "dev_runbook_id": dev_runbook_id,
                    "prod_runbook_id": prod_runbook.id,
                    "promoted_at": prod_runbook.promoted_at.isoformat()
                }
            )
            db.add(approval)
            db.commit()
            
            logger.info(
                f"Successfully promoted runbook {dev_runbook_id} to production as {prod_runbook.id} "
                f"(approved by user {approved_by})"
            )
            
            return prod_runbook, None
            
        except Exception as e:
            logger.error(f"Error promoting runbook {dev_runbook_id}: {e}", exc_info=True)
            db.rollback()
            return None, f"Promotion failed: {str(e)}"
    
    def get_promotion_history(
        self,
        db: Session,
        runbook_id: int,
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get promotion history for a runbook
        
        Args:
            db: Database session
            runbook_id: Runbook ID (can be dev or production)
            tenant_id: Tenant ID
            
        Returns:
            List of promotion records
        """
        try:
            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id
            ).first()
            
            if not runbook:
                return []
            
            history = []
            
            # If this is a production runbook, find the dev source
            if runbook.environment == "production" and runbook.promoted_from_id:
                dev_runbook = db.query(Runbook).filter(
                    Runbook.id == runbook.promoted_from_id
                ).first()
                if dev_runbook:
                    history.append({
                        "type": "promoted_from",
                        "runbook_id": dev_runbook.id,
                        "title": dev_runbook.title,
                        "environment": dev_runbook.environment,
                        "promoted_at": runbook.promoted_at.isoformat() if runbook.promoted_at else None
                    })
            
            # If this is a dev runbook, find production versions
            if runbook.environment == "dev":
                prod_runbooks = db.query(Runbook).filter(
                    Runbook.promoted_from_id == runbook_id,
                    Runbook.environment == "production"
                ).all()
                for prod in prod_runbooks:
                    history.append({
                        "type": "promoted_to",
                        "runbook_id": prod.id,
                        "title": prod.title,
                        "environment": prod.environment,
                        "promoted_at": prod.promoted_at.isoformat() if prod.promoted_at else None
                    })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting promotion history for {runbook_id}: {e}", exc_info=True)
            return []


# Global instance
_runbook_promotion_service: Optional[RunbookPromotionService] = None


def get_runbook_promotion_service() -> RunbookPromotionService:
    """Get or create runbook promotion service instance"""
    global _runbook_promotion_service
    if _runbook_promotion_service is None:
        _runbook_promotion_service = RunbookPromotionService()
    return _runbook_promotion_service

