"""
Transaction management utilities
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from app.core.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager for database transactions
    
    Usage:
        with transaction(db) as txn_db:
            # Perform operations
            txn_db.add(object)
            # Transaction commits automatically on exit
            # Rolls back on exception
    
    Args:
        db: Database session
    
    Yields:
        Database session (same as input)
    """
    try:
        yield db
        db.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise


@contextmanager
def nested_transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager for nested transactions (savepoints)
    
    Usage:
        with transaction(db) as txn_db:
            # Outer transaction
            with nested_transaction(txn_db) as nested_db:
                # Nested transaction (savepoint)
                nested_db.add(object)
                # Can rollback just this nested transaction
    
    Args:
        db: Database session
    
    Yields:
        Database session (same as input)
    """
    savepoint = db.begin_nested()
    try:
        yield db
        savepoint.commit()
        logger.debug("Nested transaction committed successfully")
    except Exception as e:
        savepoint.rollback()
        logger.debug(f"Nested transaction rolled back: {e}")
        raise



