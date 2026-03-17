"""
Repository for metadata mapping data access
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.metadata_mapping import MetadataMapping
from app.repositories.base_repository import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class MetadataMappingRepository(BaseRepository[MetadataMapping]):
    """Repository for MetadataMapping CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(MetadataMapping, db)

    def get_low_confidence_flags(
        self, tenant_id: int, min_confidence: float
    ) -> List[MetadataMapping]:
        """Get active mappings with confidence below threshold, ordered by confidence asc"""
        return (
            self.db.query(MetadataMapping)
            .filter(
                MetadataMapping.tenant_id == tenant_id,
                MetadataMapping.confidence < min_confidence,
                MetadataMapping.is_active == True,
            )
            .order_by(MetadataMapping.confidence.asc())
            .all()
        )
