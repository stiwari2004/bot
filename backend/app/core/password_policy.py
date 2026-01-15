"""
Password policy enforcement
"""
import re
from typing import List, Tuple, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class PasswordPolicy:
    """Password policy configuration and validation"""
    
    # Default policy settings
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    MAX_LENGTH = 128
    PREVENT_COMMON_PASSWORDS = True
    
    # Common passwords to prevent
    COMMON_PASSWORDS = [
        "password", "123456", "12345678", "123456789", "1234567890",
        "qwerty", "abc123", "password1", "Password1", "Password123",
        "admin", "letmein", "welcome", "monkey", "1234567", "dragon",
        "master", "sunshine", "ashley", "bailey", "passw0rd", "shadow",
        "123123", "654321", "superman", "qazwsx", "michael", "football"
    ]
    
    @classmethod
    def validate_password(cls, password: str, user_email: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate password against policy
        
        Args:
            password: Password to validate
            user_email: Optional user email to check for password similarity
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be no more than {cls.MAX_LENGTH} characters long")
        
        # Check character requirements
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if cls.REQUIRE_DIGITS and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if cls.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
        
        # Check for common passwords
        if cls.PREVENT_COMMON_PASSWORDS:
            password_lower = password.lower()
            if password_lower in [p.lower() for p in cls.COMMON_PASSWORDS]:
                errors.append("Password is too common and easily guessable")
        
        # Check for email similarity
        if user_email:
            email_local = user_email.split('@')[0].lower()
            if email_local in password.lower() or password.lower() in email_local:
                errors.append("Password should not contain your email address")
        
        # Check for repeated characters
        if re.search(r'(.)\1{3,}', password):
            errors.append("Password should not contain more than 3 repeated characters in a row")
        
        # Check for sequential characters
        if cls._has_sequential_chars(password):
            errors.append("Password should not contain obvious sequences (e.g., abc, 123)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _has_sequential_chars(password: str, min_seq: int = 3) -> bool:
        """Check if password contains sequential characters"""
        password_lower = password.lower()
        
        # Check for sequential letters
        for i in range(len(password_lower) - min_seq + 1):
            seq = password_lower[i:i+min_seq]
            if seq.isalpha() and len(seq) == min_seq:
                # Check if sequential (abc, bcd, etc.)
                if all(ord(seq[j+1]) == ord(seq[j]) + 1 for j in range(len(seq)-1)):
                    return True
        
        # Check for sequential numbers
        for i in range(len(password) - min_seq + 1):
            seq = password[i:i+min_seq]
            if seq.isdigit() and len(seq) == min_seq:
                # Check if sequential (123, 234, etc.)
                if all(int(seq[j+1]) == int(seq[j]) + 1 for j in range(len(seq)-1)):
                    return True
        
        return False
    
    @classmethod
    def get_policy_description(cls) -> str:
        """Get human-readable password policy description"""
        requirements = [f"At least {cls.MIN_LENGTH} characters"]
        
        if cls.REQUIRE_UPPERCASE:
            requirements.append("one uppercase letter")
        if cls.REQUIRE_LOWERCASE:
            requirements.append("one lowercase letter")
        if cls.REQUIRE_DIGITS:
            requirements.append("one digit")
        if cls.REQUIRE_SPECIAL:
            requirements.append("one special character")
        
        return f"Password must contain: {', '.join(requirements)}"

