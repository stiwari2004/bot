# White Labeling & Tenant Admin Implementation Plan

**Target**: MVP Sandbox Go-Live by EOD Sunday
**Status**: Planning for tomorrow morning

## Overview
Implement white labeling solution that allows tenants to customize the UI/branding without exposing source code.

## Key Requirements

### 1. Tenant Admin Section
- **Purpose**: Allow tenant admins to configure white label settings
- **Features Needed**:
  - Branding configuration (logo, colors, company name)
  - Domain/subdomain configuration
  - Theme customization
  - Email template customization
  - Custom footer/header content

### 2. White Labeling Model

#### Architecture Considerations:
- **Code Protection**: Ensure source code is not exposed in white labeling
- **Configuration-Based**: Use database/config files for customization
- **Template System**: Use template variables instead of hardcoded values
- **Asset Management**: Serve custom assets (logos, CSS) from tenant-specific paths

#### Implementation Approach:
1. **Database Model**:
   - `tenant_white_label_config` table
   - Store: logo_url, primary_color, secondary_color, company_name, domain, etc.
   - JSON field for custom CSS/JS overrides

2. **Frontend Strategy**:
   - Load tenant config on app initialization
   - Apply CSS variables for colors
   - Replace logo/images based on tenant config
   - Use environment variables for tenant identification

3. **Backend Strategy**:
   - API endpoint: `GET /api/v1/tenant/config` (public, tenant-scoped)
   - Serve custom assets from `/assets/tenant/{tenant_id}/`
   - Middleware to inject tenant config into responses

4. **Code Protection**:
   - **No source code exposure**: Only serve compiled/bundled assets
   - **Config injection**: Inject tenant config at build time or runtime (via API)
   - **Environment-based**: Use subdomain/domain to identify tenant
   - **Static assets**: Pre-compile tenant-specific builds if needed

### 3. Technical Implementation Plan

#### Phase 1: Database & Backend
- [ ] Create `tenant_white_label_config` model
- [ ] Create migration for white label config table
- [ ] Create API endpoints:
  - `GET /api/v1/admin/white-label/config` (admin only)
  - `PUT /api/v1/admin/white-label/config` (admin only)
  - `GET /api/v1/tenant/config` (public, for frontend)
- [ ] Create service to serve tenant-specific assets

#### Phase 2: Frontend Tenant Admin UI
- [ ] Create tenant admin dashboard route
- [ ] White label configuration form:
  - Logo upload
  - Color picker (primary, secondary, accent)
  - Company name/domain
  - Preview section
- [ ] Save/update white label config
- [ ] Validation for uploaded assets

#### Phase 3: Frontend White Labeling
- [ ] Create tenant config context/hook
- [ ] Load tenant config on app initialization
- [ ] Apply CSS variables for colors
- [ ] Replace logo/branding elements
- [ ] Custom header/footer based on config
- [ ] Handle subdomain/domain routing

#### Phase 4: Asset Management
- [ ] File upload endpoint for logos/assets
- [ ] Asset storage strategy (S3/local filesystem)
- [ ] Asset serving endpoint
- [ ] Image optimization/resizing

### 4. Security Considerations

- **Tenant Isolation**: Ensure tenant configs are properly scoped
- **Asset Access**: Verify tenant can only access their own assets
- **Admin Access**: Only tenant admins can modify white label config
- **Code Protection**: 
  - Never expose source code in white label builds
  - Use environment variables for tenant identification
  - Serve only compiled/bundled JavaScript
  - Use API calls for dynamic config, not embedded code

### 5. MVP Scope (For Sunday Launch)

**Must Have**:
- Basic white label config (logo, colors, company name)
- Tenant admin UI to configure these
- Frontend applies config on load
- Subdomain-based tenant identification

**Nice to Have** (Post-MVP):
- Custom domain support
- Advanced theme customization
- Email template customization
- Custom CSS injection

### 6. Database Schema (Draft)

```sql
CREATE TABLE tenant_white_label_config (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    company_name VARCHAR(255),
    logo_url VARCHAR(500),
    primary_color VARCHAR(7),  -- Hex color
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    domain VARCHAR(255),  -- Custom domain
    subdomain VARCHAR(100),  -- Subdomain identifier
    custom_css TEXT,  -- Optional custom CSS
    custom_js TEXT,  -- Optional custom JS (minified)
    footer_text TEXT,
    header_text TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id)
);

CREATE INDEX idx_white_label_tenant ON tenant_white_label_config(tenant_id);
CREATE INDEX idx_white_label_subdomain ON tenant_white_label_config(subdomain);
CREATE INDEX idx_white_label_domain ON tenant_white_label_config(domain);
```

### 7. API Endpoints (Draft)

```python
# Admin endpoints (tenant admin only)
GET  /api/v1/admin/white-label/config
PUT  /api/v1/admin/white-label/config
POST /api/v1/admin/white-label/upload-logo

# Public endpoint (for frontend)
GET  /api/v1/tenant/config?subdomain={subdomain}
GET  /api/v1/tenant/config?domain={domain}
GET  /api/v1/assets/tenant/{tenant_id}/logo
```

### 8. Frontend Routes (Draft)

```
/admin/white-label          - White label configuration page
/admin/white-label/preview  - Preview white label changes
```

### 9. Questions to Resolve Tomorrow

1. **Subdomain Strategy**: 
   - How do we identify tenant from subdomain?
   - Do we need middleware to extract tenant from request?

2. **Asset Storage**:
   - Local filesystem or S3?
   - How to handle asset cleanup on tenant deletion?

3. **Build Strategy**:
   - Runtime config injection (API call) vs Build-time config?
   - Do we need separate builds per tenant?

4. **Code Protection**:
   - How to ensure no source code leaks?
   - Should we use environment variables or API-based config?

5. **MVP Scope**:
   - What's the minimum viable white labeling for Sunday?
   - Can we start with just logo + colors?

## Next Steps (Tomorrow Morning)

1. Review and finalize this plan
2. Create database migration for white label config
3. Implement backend API endpoints
4. Create tenant admin UI
5. Implement frontend white labeling
6. Test with multiple tenants
7. Deploy to sandbox environment

## Notes

- **Code Protection**: The key is to never embed source code. Use:
  - Compiled/bundled JavaScript only
  - API-based configuration
  - Environment variables for tenant identification
  - Template-based rendering (not code injection)

- **Performance**: Consider caching tenant configs to avoid DB hits on every request

- **Fallback**: Always have a default theme if tenant config is missing




