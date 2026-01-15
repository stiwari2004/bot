# Pagination Migration Guide

This guide shows how to migrate existing list endpoints to use the standardized pagination utilities.

## Before (Current Implementation)

```python
@router.get("/", response_model=List[RunbookResponse])
async def list_runbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    controller = RunbookController(db, current_user.tenant_id)
    result = controller.list_runbooks(skip, limit)
    return result
```

## After (Standardized Pagination)

```python
from app.core.pagination import PaginationParams, PaginatedResponse, paginate_query

@router.get("/", response_model=PaginatedResponse[RunbookResponse])
async def list_runbooks(
    pagination: PaginationParams = Depends(PaginationParams.from_query),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Build query
    query = db.query(Runbook).filter(Runbook.tenant_id == current_user.tenant_id)
    
    # Apply pagination
    paginated_query, total = paginate_query(
        query,
        page=pagination.page,
        per_page=pagination.per_page
    )
    
    # Execute query
    runbooks = paginated_query.all()
    
    # Convert to response models
    items = [RunbookResponse.from_orm(rb) for rb in runbooks]
    
    # Return paginated response
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page
    )
```

## Response Format

### Before
```json
[
  {"id": 1, "title": "..."},
  {"id": 2, "title": "..."}
]
```

### After
```json
{
  "items": [
    {"id": 1, "title": "..."},
    {"id": 2, "title": "..."}
  ],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": false
}
```

## Migration Steps

1. **Import pagination utilities**
   ```python
   from app.core.pagination import PaginationParams, PaginatedResponse, paginate_query
   ```

2. **Update endpoint signature**
   - Replace `skip` and `limit` parameters with `PaginationParams`
   - Change response model from `List[T]` to `PaginatedResponse[T]`

3. **Update query logic**
   - Use `paginate_query()` instead of manual `offset()`/`limit()`
   - Get total count from `paginate_query()` return value

4. **Update response**
   - Use `PaginatedResponse.create()` to build response
   - Include all pagination metadata

5. **Update frontend** (if needed)
   - Update API calls to use `page` and `per_page` instead of `skip` and `limit`
   - Update response parsing to access `items` array
   - Use pagination metadata (`has_next`, `has_prev`, `pages`) for UI

## Endpoints to Migrate

Priority order:
1. ✅ `GET /api/v1/runbooks/` - High traffic
2. ✅ `GET /api/v1/tickets/` - High traffic
3. ✅ `GET /api/v1/executions/` - High traffic
4. `GET /api/v1/documents/` - Medium traffic
5. `GET /api/v1/alerts/` - Medium traffic
6. Other list endpoints as needed

## Backward Compatibility

If you need to maintain backward compatibility with existing clients:

```python
@router.get("/", response_model=Union[List[RunbookResponse], PaginatedResponse[RunbookResponse]])
async def list_runbooks(
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
    skip: Optional[int] = Query(None, ge=0),  # Legacy parameter
    limit: Optional[int] = Query(None, ge=1, le=100),  # Legacy parameter
    use_pagination: bool = Query(False),  # Feature flag
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if use_pagination or (page is not None and per_page is not None):
        # Use new pagination
        pagination = PaginationParams(page=page or 1, per_page=per_page or 20)
        # ... new pagination logic
    else:
        # Use legacy pagination
        skip = skip or 0
        limit = limit or 20
        # ... legacy logic
```
