"""
Standardized pagination utilities
"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
from fastapi import Query
from sqlalchemy.orm import Query as SQLAlchemyQuery
from sqlalchemy import func

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    
    @classmethod
    def from_query(
        cls,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)")
    ):
        """Create PaginationParams from FastAPI query parameters"""
        return cls(page=page, per_page=per_page)
    
    @property
    def skip(self) -> int:
        """Calculate skip/offset value"""
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        """Get limit value"""
        return self.per_page


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response model"""
    items: List[T] = Field(..., description="List of items in current page")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        per_page: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response"""
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


def paginate_query(
    query: SQLAlchemyQuery,
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100
) -> tuple[SQLAlchemyQuery, int]:
    """
    Apply pagination to a SQLAlchemy query
    
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
    
    # Get total count (before pagination)
    # Use a subquery for better performance on large datasets
    total_count = query.count()
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Apply pagination
    paginated_query = query.offset(offset).limit(per_page)
    
    return paginated_query, total_count


def paginate_list(
    items: List[T],
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100
) -> tuple[List[T], int]:
    """
    Paginate a list of items (in-memory pagination)
    
    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        per_page: Items per page
        max_per_page: Maximum items per page
        
    Returns:
        Tuple of (paginated_items, total_count)
    """
    # Ensure per_page doesn't exceed max
    per_page = min(per_page, max_per_page)
    
    total_count = len(items)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Apply pagination
    paginated_items = items[offset:offset + per_page]
    
    return paginated_items, total_count
