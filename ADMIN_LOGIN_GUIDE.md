# Admin Login Guide

## 🔐 Admin Login Endpoint

**Endpoint**: `POST http://localhost:8000/api/v1/auth/login`

**Content-Type**: `application/x-www-form-urlencoded`

**Request Body**:
```
username=<email>&password=<password>
```

**Response**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## 👤 Default Admin Credentials

### Option 1: Default Admin (from seed data)
- **Email**: `admin@example.com`
- **Password**: `admin123`

### Option 2: Demo User
- **Email**: `demo@example.com`
- **Password**: `demo123`

### Option 3: Test User
- **Email**: `test@example.com`
- **Password**: `test123`

---

## 🚀 Creating a New Admin User

If the default admin user doesn't exist, you can create one using the script:

```bash
# From the backend directory
python scripts/create_admin_user.py

# Or with custom credentials
python scripts/create_admin_user.py your-email@example.com your-password "Your Tenant Name"
```

Or use the Admin API (if you have another admin user):
```bash
POST /api/v1/admin/users
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "email": "newadmin@example.com",
  "password": "secure-password",
  "full_name": "New Admin",
  "role": "admin",
  "tenant_id": 1
}
```

---

## 🔧 Troubleshooting

### Error: `ERR_EMPTY_RESPONSE`

This means the backend server is not running. To fix:

1. **Check if backend is running**:
   ```bash
   # Check if port 8000 is in use
   netstat -an | findstr :8000  # Windows
   lsof -i :8000                # Mac/Linux
   ```

2. **Start the backend**:
   ```bash
   cd backend
   # Activate virtual environment if using one
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Or use Docker**:
   ```bash
   docker-compose up backend
   ```

### Error: "Incorrect username or password"

1. **Check if user exists**:
   ```bash
   # Run the seed script
   python scripts/create_admin_user.py
   ```

2. **Verify database is initialized**:
   ```bash
   # The seed script will create the user if it doesn't exist
   python scripts/create_admin_user.py admin@example.com admin123
   ```

### Error: "Could not validate credentials"

- Token might be expired
- Token might be invalid
- Try logging in again to get a new token

---

## 📝 Testing Login with cURL

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"

# Use the token
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <your-token-here>"
```

---

## 🎯 Quick Start

1. **Ensure backend is running** on `http://localhost:8000`
2. **Create admin user** (if needed):
   ```bash
   cd backend
   python scripts/create_admin_user.py
   ```
3. **Login via frontend** or API:
   - Email: `admin@example.com`
   - Password: `admin123`
4. **Access Admin Dashboard** in the frontend (visible only to admin users)

---

## 🔒 Security Notes

- **Change default passwords** in production!
- Use strong passwords for admin accounts
- Consider using environment variables for admin credentials
- Enable 2FA for production deployments







