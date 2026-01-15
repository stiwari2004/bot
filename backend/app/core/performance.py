"""
Performance optimization utilities
"""
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager
from sqlalchemy import select
from app.core.logging import get_logger
import time

logger = get_logger(__name__)


def eager_load_relationships(query, relationships: list[str]):
    """
    Apply eager loading to a query to prevent N+1 queries
    
    Args:
        query: SQLAlchemy query object
        relationships: List of relationship paths to eager load
        
    Returns:
        Query with eager loading applied
    """
    for rel in relationships:
        if '.' in rel:
            # Handle nested relationships (e.g., 'runbook.tenant')
            parts = rel.split('.')
            current = joinedload(parts[0])
            for part in parts[1:]:
                current = current.joinedload(part)
            query = query.options(current)
        else:
            # Simple relationship
            query = query.options(joinedload(rel))
    return query


def paginate_query(query, page: int = 1, per_page: int = 20, max_per_page: int = 100):
    """
    Apply pagination to a query
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page
        max_per_page: Maximum items per page
        
    Returns:
        Tuple of (paginated_query, total_count)
    """
    # Ensure per_page doesn't exceed max
    per_page = min(per_page, max_per_page)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get total count (before pagination)
    total_count = query.count()
    
    # Apply pagination
    paginated_query = query.offset(offset).limit(per_page)
    
    return paginated_query, total_count


def timing_middleware(func: Callable) -> Callable:
    """
    Decorator to measure and log function execution time
    
    Usage:
        @timing_middleware
        async def my_function():
            ...
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class QueryOptimizer:
    """Helper class for optimizing database queries"""
    
    @staticmethod
    def optimize_runbook_query(query, include_tenant: bool = True, include_steps: bool = False):
        """Optimize runbook query with eager loading"""
        if include_tenant:
            query = query.options(joinedload('tenant'))
        if include_steps:
            query = query.options(selectinload('steps'))
        return query
    
    @staticmethod
    def optimize_ticket_query(query, include_runbooks: bool = True, include_tenant: bool = True):
        """Optimize ticket query with eager loading"""
        if include_tenant:
            query = query.options(joinedload('tenant'))
        if include_runbooks:
            # Tickets have matched_runbooks in meta_data, not a direct relationship
            # But we can optimize the runbook lookup if needed
            pass
        return query
    
    @staticmethod
    def optimize_execution_query(query, include_runbook: bool = True, include_ticket: bool = True):
        """Optimize execution session query with eager loading"""
        if include_runbook:
            query = query.options(joinedload('runbook'))
        if include_ticket:
            query = query.options(joinedload('ticket'))
        return query


