"""
Role service for RBAC system
Handles role management and assignment
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)


class RoleService:
    """Service for managing roles"""
    
    @staticmethod
    def get_role(db: Session, role_id: int) -> Optional[Role]:
        """Get a role by ID"""
        return db.query(Role).filter(Role.id == role_id).first()
    
    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Optional[Role]:
        """Get a role by name"""
        return db.query(Role).filter(Role.name == name).first()
    
    @staticmethod
    def list_roles(
        db: Session,
        tenant_id: Optional[int] = None,
        include_system: bool = True,
        include_custom: bool = True,
        is_active: Optional[bool] = None
    ) -> List[Role]:
        """
        List roles with optional filters
        
        Args:
            db: Database session
            tenant_id: Filter by tenant (None = global roles only)
            include_system: Include system roles
            include_custom: Include custom roles
            is_active: Filter by active status
        
        Returns:
            List of Role objects
        """
        query = db.query(Role)
        
        if tenant_id is not None:
            query = query.filter(
                or_(
                    Role.tenant_id == tenant_id,
                    Role.is_global == True
                )
            )
        else:
            query = query.filter(Role.is_global == True)
        
        if not include_system:
            query = query.filter(Role.is_system_role == False)
        if not include_custom:
            query = query.filter(Role.is_custom == False)
        
        if is_active is not None:
            query = query.filter(Role.is_active == is_active)
        
        return query.all()
    
    @staticmethod
    def create_role(
        db: Session,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        tenant_id: Optional[int] = None,
        permission_ids: Optional[List[int]] = None
    ) -> Role:
        """
        Create a new custom role
        
        Args:
            db: Database session
            name: Role name (must be unique)
            display_name: Human-readable name
            description: Role description
            tenant_id: Tenant ID for tenant-specific roles (None = global)
            permission_ids: List of permission IDs to assign
        
        Returns:
            Created Role object
        """
        # Check if role name already exists
        existing = db.query(Role).filter(Role.name == name).first()
        if existing:
            raise ValueError(f"Role with name '{name}' already exists")
        
        role = Role(
            name=name,
            display_name=display_name or name,
            description=description,
            is_system_role=False,
            is_custom=True,
            tenant_id=tenant_id,
            is_global=(tenant_id is None),
            is_active=True
        )
        db.add(role)
        db.flush()  # Get role ID
        
        # Assign permissions
        if permission_ids:
            for perm_id in permission_ids:
                permission = db.query(Permission).filter(Permission.id == perm_id).first()
                if permission:
                    role_perm = RolePermission(role_id=role.id, permission_id=perm_id)
                    db.add(role_perm)
        
        db.commit()
        db.refresh(role)
        logger.info(f"Created custom role: {name} (ID: {role.id})")
        return role
    
    @staticmethod
    def update_role(
        db: Session,
        role_id: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        permission_ids: Optional[List[int]] = None
    ) -> Role:
        """
        Update an existing role
        
        Args:
            db: Database session
            role_id: Role ID to update
            display_name: New display name
            description: New description
            is_active: New active status
            permission_ids: New list of permission IDs (replaces existing)
        
        Returns:
            Updated Role object
        """
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError(f"Role with ID {role_id} not found")
        
        # Don't allow modifying system roles
        if role.is_system_role:
            raise ValueError("Cannot modify system roles")
        
        if display_name is not None:
            role.display_name = display_name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active
        
        # Update permissions if provided
        if permission_ids is not None:
            # Remove existing permissions
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
            
            # Add new permissions
            for perm_id in permission_ids:
                permission = db.query(Permission).filter(Permission.id == perm_id).first()
                if permission:
                    role_perm = RolePermission(role_id=role_id, permission_id=perm_id)
                    db.add(role_perm)
        
        db.commit()
        db.refresh(role)
        logger.info(f"Updated role: {role.name} (ID: {role_id})")
        return role
    
    @staticmethod
    def delete_role(db: Session, role_id: int) -> bool:
        """
        Delete a custom role (cannot delete system roles)
        
        Args:
            db: Database session
            role_id: Role ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return False
        
        if role.is_system_role:
            raise ValueError("Cannot delete system roles")
        
        # Check if any users are using this role
        users_with_role = db.query(User).filter(User.role_id == role_id).count()
        if users_with_role > 0:
            raise ValueError(f"Cannot delete role: {users_with_role} user(s) are assigned to this role")
        
        db.delete(role)
        db.commit()
        logger.info(f"Deleted role: {role.name} (ID: {role_id})")
        return True
    
    @staticmethod
    def get_role_permissions(db: Session, role_id: int) -> List[Permission]:
        """Get all permissions for a role"""
        return db.query(Permission).join(RolePermission).filter(
            RolePermission.role_id == role_id,
            Permission.is_active == True
        ).all()
    
    @staticmethod
    def assign_permission_to_role(
        db: Session,
        role_id: int,
        permission_id: int
    ) -> RolePermission:
        """Assign a permission to a role"""
        # Check if already assigned
        existing = db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
        
        if existing:
            return existing
        
        role_perm = RolePermission(role_id=role_id, permission_id=permission_id)
        db.add(role_perm)
        db.commit()
        db.refresh(role_perm)
        return role_perm
    
    @staticmethod
    def remove_permission_from_role(
        db: Session,
        role_id: int,
        permission_id: int
    ) -> bool:
        """Remove a permission from a role"""
        role_perm = db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        ).first()
        
        if not role_perm:
            return False
        
        db.delete(role_perm)
        db.commit()
        return True


# Global instance
role_service = RoleService()

