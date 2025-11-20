"""
Base repository with common CRUD operations
"""
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common database operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_tenant(self, tenant_id: int, id: int) -> Optional[ModelType]:
        """Get a single record by ID and tenant_id"""
        return self.db.query(self.model).filter(
            and_(self.model.id == id, self.model.tenant_id == tenant_id)
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def get_by_tenant_all(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records for a tenant with pagination"""
        return self.db.query(self.model).filter(
            self.model.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update a record by ID"""
        instance = self.get(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
        return instance
    
    def delete(self, id: int) -> bool:
        """Delete a record by ID"""
        instance = self.get(id)
        if instance:
            self.db.delete(instance)
            self.db.commit()
            return True
        return False
    
    def filter_by(self, **filters) -> List[ModelType]:
        """Filter records by given criteria"""
        return self.db.query(self.model).filter_by(**filters).all()
    
    def filter_by_tenant(self, tenant_id: int, **filters) -> List[ModelType]:
        """Filter records by tenant_id and given criteria"""
        return self.db.query(self.model).filter(
            and_(self.model.tenant_id == tenant_id, **filters)
        ).all()




