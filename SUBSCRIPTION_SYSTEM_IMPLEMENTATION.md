# Subscription System Implementation

## Overview
A complete subscription/license management system that tracks and enforces limits on **seats (users)** and **nodes (infrastructure connections)** for each tenant.

## Features Implemented

### 1. Database Models
- **`TenantSubscription`**: Stores subscription limits and current usage
  - `max_seats`, `max_nodes`: Limits
  - `current_seats`, `current_nodes`: Real-time usage
  - `is_enforced`: Toggle to enable/disable enforcement
  - `monthly_price`, `seat_overage_rate`, `node_overage_rate`: Billing info
  - `status`: active, suspended, expired, cancelled
  - `expires_at`: Optional expiration date

- **`SubscriptionUsage`**: Historical usage tracking for reporting

### 2. Subscription Tracker Service
**Location**: `backend/app/services/subscription/subscription_tracker.py`

**Key Methods**:
- `get_subscription(tenant_id)`: Get active subscription for tenant
- `update_usage(tenant_id)`: Update current usage counts
- `check_seat_limit(tenant_id)`: Check if tenant can add another user
- `check_node_limit(tenant_id)`: Check if tenant can add another infrastructure connection
- `get_usage_summary(tenant_id)`: Get detailed usage summary

### 3. API Endpoints (Super Admin Only)
**Location**: `backend/app/api/v1/endpoints/subscriptions.py`

**Endpoints**:
- `POST /api/v1/subscriptions/subscriptions`: Create subscription
- `GET /api/v1/subscriptions/subscriptions`: List all subscriptions
- `GET /api/v1/subscriptions/subscriptions/{id}`: Get subscription details
- `PUT /api/v1/subscriptions/subscriptions/{id}`: Update subscription
- `GET /api/v1/subscriptions/tenant/{tenant_id}/usage`: Get usage summary

### 4. Enforcement Integration

#### User Creation Enforcement
**Location**: `backend/app/api/v1/endpoints/super_admin.py`

When creating a user:
```python
tracker = SubscriptionTracker(db)
allowed, error_msg = tracker.check_seat_limit(tenant_id)
if not allowed:
    raise HTTPException(status_code=403, detail=error_msg)
```

#### Infrastructure Connection Enforcement
**Location**: `backend/app/controllers/connector_controller.py`

When creating infrastructure connection:
```python
tracker = SubscriptionTracker(self.db)
allowed, error_msg = tracker.check_node_limit(self.tenant_id)
if not allowed:
    raise self.bad_request(error_msg)
```

### 5. Frontend UI
**Location**: `frontend-nextjs/src/app/super-admin/subscriptions/page.tsx`

**Features**:
- List all subscriptions with usage indicators
- Create new subscriptions
- Edit existing subscriptions
- View real-time usage (seats/nodes)
- Visual indicators for exceeded limits
- Badges for low/exceeded limits

**Access**: Super Admin Dashboard → "Subscription Management"

## How It Works

### 1. Creating a Subscription
1. Super Admin navigates to `/super-admin/subscriptions`
2. Clicks "Create Subscription"
3. Selects tenant, sets limits (seats, nodes), pricing, and enforcement settings
4. System creates subscription and initializes usage tracking

### 2. Usage Tracking
- **Seats**: Counted from active users (`User.is_active = True`)
- **Nodes**: Counted from active infrastructure connections (`InfrastructureConnection.is_active = True`)
- Usage is updated automatically when:
  - Creating users
  - Creating infrastructure connections
  - Viewing subscription details

### 3. Enforcement
When `is_enforced = True`:
- **User Creation**: Blocked if `current_seats >= max_seats`
- **Infrastructure Connection Creation**: Blocked if `current_nodes >= max_nodes`
- Returns clear error messages: "Seat limit reached (14/14). Please upgrade your subscription or contact support."

### 4. Usage Monitoring
- Real-time usage displayed in subscription list
- Color-coded indicators:
  - **Green**: Normal usage
  - **Yellow**: Low remaining (≤2 seats or ≤10 nodes)
  - **Red**: Limit exceeded
- Badges show "Exceeded" or "Low" status

## Database Schema

```sql
CREATE TABLE tenant_subscriptions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL UNIQUE,
    max_seats INTEGER NOT NULL,
    max_nodes INTEGER NOT NULL,
    current_seats INTEGER NOT NULL DEFAULT 0,
    current_nodes INTEGER NOT NULL DEFAULT 0,
    subscription_name VARCHAR(255) NULL,
    monthly_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    seat_overage_rate NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    node_overage_rate NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_enforced BOOLEAN NOT NULL DEFAULT TRUE,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NULL,
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    notes VARCHAR(500) NULL,
    created_by INTEGER REFERENCES super_admins(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Example Usage

### Create Subscription for MSP
```json
POST /api/v1/subscriptions/subscriptions
{
  "tenant_id": 2,
  "max_seats": 14,
  "max_nodes": 1000,
  "subscription_name": "MSP Starter Bundle",
  "monthly_price": 24999,
  "seat_overage_rate": 499,
  "node_overage_rate": 199,
  "is_enforced": true,
  "auto_renew": true
}
```

### Check Usage
```json
GET /api/v1/subscriptions/tenant/2/usage
{
  "has_subscription": true,
  "subscription_id": 1,
  "seats": {
    "current": 12,
    "max": 14,
    "remaining": 2,
    "exceeded": false,
    "usage_percent": 85.71
  },
  "nodes": {
    "current": 850,
    "max": 1000,
    "remaining": 150,
    "exceeded": false,
    "usage_percent": 85.0
  }
}
```

## Key Benefits

1. **Simple Model**: Just 2 metrics (seats + nodes)
2. **Real-time Enforcement**: Blocks actions when limits reached
3. **Flexible**: Can disable enforcement per subscription
4. **Transparent**: Clear usage indicators and error messages
5. **Scalable**: Easy to add more metrics later if needed

## Next Steps

1. **Periodic Usage Updates**: Background job to update usage hourly/daily
2. **Usage Alerts**: Email notifications when approaching limits
3. **Usage Reports**: Monthly usage reports for billing
4. **Auto-upgrade Prompts**: Suggest upgrades when limits consistently exceeded
5. **MSP Customer Subscriptions**: Allow MSPs to create subscriptions for their customers

## Testing

To test the system:
1. Create a subscription with low limits (e.g., 2 seats, 5 nodes)
2. Try creating users until limit is reached
3. Try creating infrastructure connections until limit is reached
4. Verify error messages are clear
5. Disable enforcement and verify actions are allowed
6. Re-enable enforcement and verify blocking works again


