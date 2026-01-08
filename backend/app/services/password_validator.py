"""
Password validation service
"""
import re
from typing import List, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)


class PasswordValidator:
    """Service for validating password strength and history"""
    
    # Minimum requirements
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBER = True
    REQUIRE_SPECIAL = True
    MAX_HISTORY = 5  # Keep last 5 passwords
    
    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Length check
        if len(password) < self.MIN_LENGTH:
            errors.append(f"Password must be at least {self.MIN_LENGTH} characters long")
        
        # Uppercase check
        if self.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Lowercase check
        if self.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Number check
        if self.REQUIRE_NUMBER and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        # Special character check
        if self.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            errors.append("Password must contain at least one special character")
        
        return (len(errors) == 0, errors)
    
    def check_password_history(
        self,
        password: str,
        password_hash: str,
        password_history: List[str]
    ) -> Tuple[bool, str]:
        """
        Check if password was recently used (in history)
        
        Args:
            password: Plain text password to check
            password_hash: Current password hash (to exclude from check)
            password_history: List of previous password hashes
            
        Returns:
            (is_reused, error_message)
        """
        from app.services.auth import verify_password
        
        # Check against history (excluding current password)
        for old_hash in password_history:
            if old_hash == password_hash:
                continue  # Skip current password
            if verify_password(password, old_hash):
                return (True, "Password cannot be one of your last 5 passwords")
        
        return (False, "")
    
    def add_to_history(
        self,
        new_password_hash: str,
        current_history: List[str],
        current_password_hash: str
    ) -> List[str]:
        """
        Add new password hash to history, keeping only last N
        
        Args:
            new_password_hash: Hash of new password
            current_history: Current password history list
            current_password_hash: Current password hash (to add to history)
            
        Returns:
            Updated password history list
        """
        # Ensure history is a list
        if not isinstance(current_history, list):
            current_history = []
        
        # Add current password to history (if not already there)
        if current_password_hash and current_password_hash not in current_history:
            current_history.append(current_password_hash)
        
        # Keep only last MAX_HISTORY entries
        if len(current_history) > self.MAX_HISTORY:
            current_history = current_history[-self.MAX_HISTORY:]
        
        return current_history
    
    def calculate_expiration_date(self, days: int = 90) -> 'datetime':
        """
        Calculate password expiration date
        
        Args:
            days: Number of days until expiration (default 90)
            
        Returns:
            Expiration datetime
        """
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone.utc) + timedelta(days=days)
    
    def is_password_expired(self, password_expires_at: 'datetime') -> bool:
        """
        Check if password is expired
        
        Args:
            password_expires_at: Expiration datetime
            
        Returns:
            True if expired, False otherwise
        """
        if not password_expires_at:
            return False
        
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > password_expires_at


# Global instance
_password_validator: PasswordValidator = None


def get_password_validator() -> PasswordValidator:
    """Get or create password validator instance"""
    global _password_validator
    if _password_validator is None:
        _password_validator = PasswordValidator()
    return _password_validator

