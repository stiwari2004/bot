# Login Troubleshooting Guide

## Admin Login Credentials

- **Email**: `admin@example.com`
- **Password**: `admin123`
- **Endpoint**: `POST http://localhost:8000/api/v1/auth/login`

## Verification

The admin user has been created and verified. You can test the login directly:

### Test Login via PowerShell:
```powershell
$body = "username=admin@example.com&password=admin123"
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $body -ContentType "application/x-www-form-urlencoded"
```

### Test Login via curl (if available):
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

## Common Issues

### 1. "Cannot connect to backend" Error

**Symptom**: Frontend shows "Cannot connect to backend at http://localhost:8000/api/v1/auth/login"

**Solution**:
- Verify backend is running: `docker-compose ps`
- Check backend logs: `docker-compose logs backend`
- Ensure backend is accessible: Open `http://localhost:8000/docs` in browser

### 2. CORS Error

**Symptom**: Browser console shows CORS error

**Solution**:
- Backend CORS is configured for `http://localhost:3000` in development
- Check `backend/.env` has `ENVIRONMENT=development`
- Verify `ALLOWED_HOSTS` includes `http://localhost:3000`

### 3. "Incorrect username or password" Error

**Symptom**: Login form shows authentication error

**Solution**:
- Verify admin user exists: Run `docker-compose exec backend python scripts/create_admin_user.py admin@example.com admin123 1`
- Check user is active: The script will confirm if user exists and is active

### 4. Network Error / Empty Response

**Symptom**: `net::ERR_EMPTY_RESPONSE` in browser console

**Solution**:
- Backend may have crashed or not started properly
- Check backend container: `docker-compose ps backend`
- Restart backend: `docker-compose restart backend`
- Check backend logs: `docker-compose logs -f backend`

### 5. Frontend Not Connecting

**Symptom**: Frontend shows loading but never completes

**Solution**:
- Check browser console (F12) for errors
- Verify `NEXT_PUBLIC_API_BASE_URL` is set correctly (or defaults to `http://localhost:8000`)
- Test backend health: `http://localhost:8000/health`

## Creating Admin User

If the admin user doesn't exist, create it:

```bash
docker-compose exec backend python scripts/create_admin_user.py admin@example.com admin123 1
```

This will:
- Use tenant ID 1 (demo tenant)
- Create user with email `admin@example.com`
- Set password to `admin123`
- Assign admin role

## Testing the Full Flow

1. **Backend Health Check**:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/health"
   ```

2. **Login Test**:
   ```powershell
   $body = "username=admin@example.com&password=admin123"
   $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $body -ContentType "application/x-www-form-urlencoded"
   $token = ($response.Content | ConvertFrom-Json).access_token
   ```

3. **Get User Info**:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/me" -Method GET -Headers @{"Authorization"="Bearer $token"}
   ```

## Frontend Login

The frontend login page is at `http://localhost:3000`. 

- If you see the login form, the frontend is running
- Enter credentials: `admin@example.com` / `admin123`
- If login fails, check browser console (F12) for detailed error messages

## Debugging Steps

1. **Check Backend Status**:
   ```bash
   docker-compose ps
   docker-compose logs backend | tail -50
   ```

2. **Check Frontend Status**:
   - Open `http://localhost:3000` in browser
   - Open Developer Tools (F12)
   - Check Console tab for errors
   - Check Network tab for failed requests

3. **Verify API Endpoint**:
   - Frontend uses: `http://localhost:8000/api/v1/auth/login`
   - Backend should be running on port 8000
   - Check `frontend-nextjs/src/lib/api-config.ts` for API_BASE_URL

4. **Check CORS**:
   - Backend allows `http://localhost:3000` in development
   - Verify `ENVIRONMENT=development` in `backend/.env`

## Still Having Issues?

1. Check backend logs: `docker-compose logs -f backend`
2. Check frontend console: Open browser DevTools (F12)
3. Verify both services are running: `docker-compose ps`
4. Try restarting both: `docker-compose restart`







