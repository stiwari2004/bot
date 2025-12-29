# Licensing Model Implementation Plan

## Overview
A comprehensive licensing system that defines license plans/tiers and enforces feature access based on the tenant's active license.

## Proposed License Tiers

### 1. Free/Trial
- **Seats**: 3 users
- **Nodes**: 5 infrastructure connections
- **Features**: 
  - Basic runbook execution
  - Ticket viewing
  - Limited integrations (ServiceNow only)
  - No RBAC (legacy roles only)
  - No SolarWinds
  - No advanced analytics

### 2. Starter
- **Seats**: 10 users
- **Nodes**: 20 infrastructure connections
- **Features**:
  - All Free features
  - Basic RBAC (predefined roles only)
  - Multiple ticketing integrations
  - Basic monitoring integrations
  - API access (limited rate)

### 3. Professional
- **Seats**: 50 users
- **Nodes**: 100 infrastructure connections
- **Features**:
  - All Starter features
  - Full RBAC (custom roles + permissions)
  - All monitoring integrations (including SolarWinds)
  - Advanced analytics
  - Priority support
  - Higher API rate limits

### 4. Enterprise
- **Seats**: Unlimited
- **Nodes**: Unlimited
- **Features**:
  - All Professional features
  - Custom integrations
  - White-labeling
  - Dedicated support
  - SLA guarantees
  - On-premise deployment option

## Implementation Components

### 1. License Plan Model
- Define license plans with feature flags
- Map features to plans
- Store plan assignments per tenant

### 2. License Service
- Check if tenant has access to a feature
- Enforce license limits (seats, nodes)
- Validate license expiration
- Handle license upgrades/downgrades

### 3. License Middleware
- Decorator to protect endpoints by feature
- Automatic license checking
- Graceful degradation for missing features

### 4. License Management UI
- View current license and usage
- Upgrade/downgrade options
- Feature comparison table
- Usage dashboards

### 5. Integration Points
- User creation: Check seat limits
- Infrastructure connection: Check node limits
- Feature access: Check license tier
- API endpoints: Enforce feature-based access

## Questions for You

1. **License Tiers**: Do you want the 4 tiers above, or different ones?
2. **Feature Gating**: Which specific features should be gated?
3. **Integration**: Should licenses be separate from subscriptions, or integrated?
4. **Enforcement**: Strict (block) or soft (warn but allow)?
5. **Trial Period**: Should there be a trial period for paid plans?



