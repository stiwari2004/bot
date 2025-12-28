"""
Permission service for RBAC system
Handles permission checking and user authorization
"""
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_permission import UserPermission
from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionService:
    """Service for checking and managing permissions"""
    
    @staticmethod
    def has_permission(
        db: Session,
        user: User,
        permission_name: str,
        tenant_id: Optional[int] = None
    ) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            db: Database session
            user: User object
            permission_name: Permission name (e.g., "read:tickets")
            tenant_id: Optional tenant ID for tenant-scoped checks
        
        Returns:
            True if user has permission, False otherwise
        """
        # Super admin always has all permissions
        if user.role == "super_admin" or (user.role_obj and user.role_obj.name == "super_admin"):
            return True
        
        # Check tenant scope if provided
        if tenant_id and user.tenant_id != tenant_id:
            # User can only access their own tenant unless they have cross-tenant permissions
            if not PermissionService.has_permission(db, user, "manage:system"):
                return False
        
        # Get permission object
        permission = db.query(Permission).filter(
            Permission.name == permission_name,
            Permission.is_active == True
        ).first()
        
        if not permission:
            logger.warning(f"Permission '{permission_name}' not found")
            return False
        
        # Check user-specific permission overrides (deny takes precedence)
        user_perm = db.query(UserPermission).filter(
            UserPermission.user_id == user.id,
            UserPermission.permission_id == permission.id
        ).first()
        
        if user_perm:
            # User-specific override exists
            return user_perm.is_granted
        
        # Check role permissions
        if user.role_id:
            # New RBAC system - check role permissions
            role_perm = db.query(RolePermission).filter(
                RolePermission.role_id == user.role_id,
                RolePermission.permission_id == permission.id
            ).first()
            
            if role_perm:
                return True
        
        # Fallback to legacy role string mapping
        return PermissionService._check_legacy_role_permission(user.role, permission_name)
    
    @staticmethod
    def _check_legacy_role_permission(role: str, permission_name: str) -> bool:
        """
        Check permission based on legacy role string
        Maps old role system to new permission system
        """
        # Legacy role to permission mapping
        legacy_permissions = {
            "super_admin": {
                # Super admin has all permissions
                "read:*", "write:*", "delete:*", "execute:*", "manage:*"
            },
            "tenant_admin": {
                "read:*", "write:*", "delete:*", "execute:*",
                "read:tickets", "write:tickets", "delete:tickets",
                "read:runbooks", "write:runbooks", "execute:runbooks",
                "read:users", "write:users", "delete:users",
                "read:credentials", "write:credentials",
                "manage:tenant"
            },
            "msp_admin": {
                "read:*", "write:*", "execute:*",
                "read:tickets", "write:tickets",
                "read:runbooks", "write:runbooks", "execute:runbooks",
                "read:users", "write:users",
                "read:credentials",
                "manage:tenant"
            },
            "admin": {  # Legacy admin role
                "read:*", "write:*", "execute:*",
                "read:tickets", "write:tickets",
                "read:runbooks", "write:runbooks", "execute:runbooks",
                "read:users", "write:users",
                "manage:tenant"
            },
            "operator": {
                "read:tickets", "write:tickets",
                "read:runbooks", "write:runbooks", "execute:runbooks",
                "read:users"
            },
            "user": {
                "read:tickets", "read:runbooks", "write:runbooks", "execute:runbooks"
            },
            "viewer": {
                "read:tickets", "read:runbooks", "read:users"
            }
        }
        
        role_perms = legacy_permissions.get(role, set())
        
        # Check exact match
        if permission_name in role_perms:
            return True
        
        # Check wildcard matches
        action, resource = permission_name.split(":", 1) if ":" in permission_name else (permission_name, "")
        
        # Check action wildcard (e.g., "read:*")
        if f"{action}:*" in role_perms:
            return True
        
        # Check resource wildcard (e.g., "*:tickets")
        if f"*:{resource}" in role_perms:
            return True
        
        # Check full wildcard
        if "*:*" in role_perms:
            return True
        
        return False
    
    @staticmethod
    def get_user_permissions(db: Session, user: User) -> Set[str]:
        """
        Get all permissions for a user (from role + user overrides)
        
        Returns:
            Set of permission names
        """
        permissions = set()
        
        # Get permissions from role
        if user.role_id:
            role_perms = db.query(Permission).join(RolePermission).filter(
                RolePermission.role_id == user.role_id,
                Permission.is_active == True
            ).all()
            permissions.update([p.name for p in role_perms])
        
        # Apply user-specific overrides
        user_perms = db.query(UserPermission).join(Permission).filter(
            UserPermission.user_id == user.id,
            Permission.is_active == True
        ).all()
        
        for user_perm in user_perms:
            if user_perm.is_granted:
                permissions.add(user_perm.permission.name)
            else:
                permissions.discard(user_perm.permission.name)
        
        # Fallback to legacy role permissions
        if not permissions and user.role:
            legacy_perms = PermissionService._get_legacy_role_permissions(user.role)
            permissions.update(legacy_perms)
        
        return permissions
    
    @staticmethod
    def _get_legacy_role_permissions(role: str) -> Set[str]:
        """Get permissions for legacy role string"""
        # This is a simplified version - in practice, you'd want to map to actual permission names
        legacy_mapping = {
            "super_admin": {"*:*"},
            "tenant_admin": {"read:*", "write:*", "delete:*", "execute:*", "manage:tenant"},
            "msp_admin": {"read:*", "write:*", "execute:*", "manage:tenant"},
            "admin": {"read:*", "write:*", "execute:*", "manage:tenant"},
            "operator": {"read:tickets", "write:tickets", "read:runbooks", "write:runbooks", "execute:runbooks"},
            "user": {"read:tickets", "read:runbooks", "write:runbooks", "execute:runbooks"},
            "viewer": {"read:tickets", "read:runbooks", "read:users"}
        }
        return legacy_mapping.get(role, set())
    
    @staticmethod
    def initialize_default_permissions(db: Session) -> None:
        """
        Initialize default permissions in the database
        Should be called during system setup/migration
        """
        default_permissions = [
            # Tickets
            {"name": "read:tickets", "action": "read", "resource": "tickets", "description": "View tickets"},
            {"name": "write:tickets", "action": "write", "resource": "tickets", "description": "Create and update tickets"},
            {"name": "delete:tickets", "action": "delete", "resource": "tickets", "description": "Delete tickets"},
            
            # Runbooks
            {"name": "read:runbooks", "action": "read", "resource": "runbooks", "description": "View runbooks"},
            {"name": "write:runbooks", "action": "write", "resource": "runbooks", "description": "Create and update runbooks"},
            {"name": "delete:runbooks", "action": "delete", "resource": "runbooks", "description": "Delete runbooks"},
            {"name": "execute:runbooks", "action": "execute", "resource": "runbooks", "description": "Execute runbooks"},
            
            # Users
            {"name": "read:users", "action": "read", "resource": "users", "description": "View users"},
            {"name": "write:users", "action": "write", "resource": "users", "description": "Create and update users"},
            {"name": "delete:users", "action": "delete", "resource": "users", "description": "Delete users"},
            
            # Credentials
            {"name": "read:credentials", "action": "read", "resource": "credentials", "description": "View credentials"},
            {"name": "write:credentials", "action": "write", "resource": "credentials", "description": "Create and update credentials"},
            {"name": "delete:credentials", "action": "delete", "resource": "credentials", "description": "Delete credentials"},
            
            # Tenant management
            {"name": "manage:tenant", "action": "manage", "resource": "tenant", "description": "Manage tenant settings and configuration"},
            
            # System management
            {"name": "manage:system", "action": "manage", "resource": "system", "description": "Manage system-wide settings (super admin only)"},
        ]
        
        for perm_data in default_permissions:
            existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
            if not existing:
                permission = Permission(**perm_data)
                db.add(permission)
        
        db.commit()
        logger.info(f"Initialized {len(default_permissions)} default permissions")
    
    @staticmethod
    def initialize_default_roles(db: Session) -> None:
        """
        Initialize default system roles with their permissions
        Should be called during system setup/migration
        """
        # Ensure permissions exist first
        PermissionService.initialize_default_permissions(db)
        
        # Define default roles and their permissions
        default_roles = {
            "viewer": {
                "display_name": "Viewer",
                "description": "Read-only access to runbooks, tickets, and analytics",
                "permissions": ["read:tickets", "read:runbooks", "read:users"]
            },
            "user": {
                "display_name": "User",
                "description": "Standard user with execution and runbook creation permissions",
                "permissions": ["read:tickets", "read:runbooks", "write:runbooks", "execute:runbooks"]
            },
            "operator": {
                "display_name": "Operator",
                "description": "Enhanced execution + runbook management",
                "permissions": ["read:tickets", "write:tickets", "read:runbooks", "write:runbooks", "execute:runbooks", "read:users"]
            },
            "tenant_admin": {
                "display_name": "Tenant Admin",
                "description": "Full tenant management",
                "permissions": ["read:tickets", "write:tickets", "delete:tickets", "read:runbooks", "write:runbooks", "delete:runbooks", "execute:runbooks", "read:users", "write:users", "delete:users", "read:credentials", "write:credentials", "manage:tenant"]
            },
            "super_admin": {
                "display_name": "Super Admin",
                "description": "Platform-level access",
                "permissions": ["read:tickets", "write:tickets", "delete:tickets", "read:runbooks", "write:runbooks", "delete:runbooks", "execute:runbooks", "read:users", "write:users", "delete:users", "read:credentials", "write:credentials", "delete:credentials", "manage:tenant", "manage:system"]
            }
        }
        
        for role_name, role_data in default_roles.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(
                    name=role_name,
                    display_name=role_data["display_name"],
                    description=role_data["description"],
                    is_system_role=True,
                    is_custom=False,
                    is_global=True
                )
                db.add(role)
                db.flush()  # Get role ID
            
            # Assign permissions to role
            for perm_name in role_data["permissions"]:
                permission = db.query(Permission).filter(Permission.name == perm_name).first()
                if permission:
                    role_perm = db.query(RolePermission).filter(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id
                    ).first()
                    if not role_perm:
                        role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                        db.add(role_perm)
        
        db.commit()
        logger.info(f"Initialized {len(default_roles)} default roles")


# Global instance
permission_service = PermissionService()

