# User Management Enhancement & Database Strategy

## 1. Enhanced User Management - Implementation Plan

### Current State
- Basic form with: Email, Password, Full Name, Role dropdown
- No permission details shown
- Password reset only available through edit form (optional field)
- No role descriptions or permission explanations

### Proposed Enhancements

#### A. Enhanced Role Selection with Permissions Display

**Role Definitions:**
```typescript
const ROLE_PERMISSIONS = {
  viewer: {
    name: "Viewer",
    description: "Read-only access to runbooks, tickets, and analytics",
    permissions: [
      "View runbooks",
      "View execution history",
      "View tickets",
      "View analytics",
      "View documents"
    ],
    restrictions: [
      "Cannot create or edit runbooks",
      "Cannot execute runbooks",
      "Cannot manage users",
      "Cannot access credentials"
    ]
  },
  user: {
    name: "User",
    description: "Standard user with execution and runbook creation permissions",
    permissions: [
      "View runbooks",
      "Create/edit runbooks",
      "Execute runbooks (with approval)",
      "View tickets",
      "View analytics",
      "View documents"
    ],
    restrictions: [
      "Cannot manage users",
      "Cannot access credentials",
      "Cannot approve executions"
    ]
  },
  tenant_admin: {
    name: "Tenant Admin",
    description: "Full tenant-level administration",
    permissions: [
      "All user permissions",
      "Manage users within tenant",
      "Manage credentials",
      "Approve executions",
      "Manage ticketing connections",
      "View tenant analytics"
    ],
    restrictions: [
      "Cannot access other tenants",
      "Cannot manage system settings"
    ]
  },
  msp_admin: {
    name: "MSP Admin",
    description: "Multi-tenant management for MSPs",
    permissions: [
      "All tenant admin permissions",
      "Manage customer tenants",
      "Create users for customers",
      "View cross-tenant analytics"
    ],
    restrictions: [
      "Cannot access super admin functions",
      "Cannot modify system configuration"
    ]
  }
};
```

#### B. Enhanced User Form Features

1. **Role Selection with Visual Permissions Card**
   - Dropdown with role selection
   - Expandable permissions card showing:
     - What the role can do (green checkmarks)
     - What the role cannot do (gray restrictions)
     - Visual permission matrix

2. **Dedicated Password Reset Button**
   - Separate "Reset Password" button in user table actions
   - Modal with:
     - Generate random password option
     - Set custom password option
     - Password strength indicator
     - "Send password reset email" option (future)

3. **User Status Management**
   - Toggle active/inactive status
   - Last login display
   - Account creation date
   - Password last changed date

4. **Additional Fields**
   - Department/Team (optional)
   - Phone number (optional)
   - Notes/Description (optional)

### Implementation Steps

1. **Backend Changes:**
   - Add password reset endpoint: `POST /api/v1/super-admin/tenants/{tenant_id}/users/{user_id}/reset-password`
   - Add user permissions info endpoint: `GET /api/v1/users/permissions/{role}`
   - Update user schema to include optional fields

2. **Frontend Changes:**
   - Create `RolePermissionsCard` component
   - Create `PasswordResetModal` component
   - Enhance `CreateUserModal` with permissions display
   - Add user status toggle in user table

---

## 2. Database Strategy Recommendation

### Current Setup: pgvector (PostgreSQL Extension)

**Pros:**
- ✅ Already implemented and working
- ✅ Single database (simpler architecture)
- ✅ No additional infrastructure needed
- ✅ ACID transactions for embeddings + metadata
- ✅ Good for demos and small-to-medium scale
- ✅ Lower operational complexity

**Cons:**
- ❌ PostgreSQL not optimized for vector operations
- ❌ Slower at scale (millions of vectors)
- ❌ Limited vector-specific features
- ❌ Can impact PostgreSQL performance

### Production Alternative: Qdrant (Dedicated Vector DB)

**Pros:**
- ✅ Optimized for vector search
- ✅ Better performance at scale
- ✅ Advanced vector features (filtering, hybrid search)
- ✅ Horizontal scaling
- ✅ Better separation of concerns

**Cons:**
- ❌ Additional infrastructure to manage
- ❌ Requires data synchronization between Postgres and Qdrant
- ❌ More complex deployment
- ❌ Additional operational overhead

### **RECOMMENDATION: Hybrid Approach**

#### Phase 1: Continue with pgvector (Now - Demos)
**Rationale:**
- You're actively doing demos
- pgvector is working fine for current scale
- No need to introduce complexity during demos
- Focus on product features, not infrastructure

**Action:** Keep pgvector, monitor performance

#### Phase 2: Plan Migration to Qdrant (Production Prep)
**When to migrate:**
- When you have 100K+ documents/embeddings
- When vector search becomes a bottleneck
- When you need advanced vector features
- When preparing for production scale

**Migration Strategy:**
1. Keep abstraction layer (already have `VectorStore` interface)
2. Implement `QdrantVectorStore` alongside `PgVectorStore`
3. Feature flag to switch between implementations
4. Gradual migration: new embeddings → Qdrant, old → pgvector
5. Eventually deprecate pgvector

### Implementation Plan

**Option A: Stay with pgvector (Recommended for now)**
```yaml
Pros:
  - Zero migration effort
  - Simpler operations
  - Good enough for demos and early production
  
Action:
  - Monitor vector search performance
  - Set threshold: migrate when >100K embeddings or >500ms search time
```

**Option B: Migrate to Qdrant now**
```yaml
Pros:
  - Future-proof
  - Better scalability
  - Production-ready architecture
  
Cons:
  - Migration effort (1-2 days)
  - Additional infrastructure
  - More complex deployment
  
Action:
  - Add Qdrant to docker-compose
  - Implement QdrantVectorStore
  - Migrate existing embeddings
  - Update deployment scripts
```

---

## 3. Recommended Action Plan

### Immediate (This Week)
1. ✅ **Enhance User Management UI**
   - Add role permissions display
   - Add dedicated password reset
   - Make form more interactive
   - Estimated: 4-6 hours

### Short Term (Next 2 Weeks)
2. ✅ **Continue with pgvector**
   - Monitor performance metrics
   - Set up performance monitoring
   - Document current limitations

### Medium Term (When Scaling)
3. ⏳ **Plan Qdrant Migration**
   - When approaching 50K+ embeddings
   - Before production launch
   - Implement abstraction layer first

---

## 4. Code Structure for Enhanced User Management

### New Components Needed:

1. **`RolePermissionsCard.tsx`**
   - Displays permissions for selected role
   - Visual permission matrix
   - Expandable details

2. **`PasswordResetModal.tsx`**
   - Dedicated password reset flow
   - Password generation
   - Strength indicator

3. **`EnhancedUserForm.tsx`**
   - Combines all enhancements
   - Better UX with sections
   - Validation and feedback

### Backend Endpoints Needed:

```python
# Password reset endpoint
POST /api/v1/super-admin/tenants/{tenant_id}/users/{user_id}/reset-password
Body: { "new_password": "..." } or { "generate": true }

# Get role permissions
GET /api/v1/users/permissions/{role}
Response: { "role": "...", "permissions": [...], "restrictions": [...] }
```

---

## Decision Summary

**User Management:** ✅ **Enhance now** - Critical for demos and user experience

**Database Strategy:** ✅ **Stay with pgvector for now**, plan Qdrant migration for production scale

**Priority:** User management enhancements are more important than database migration at this stage.

