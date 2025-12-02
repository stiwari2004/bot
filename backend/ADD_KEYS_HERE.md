# How to Add Your Generated Keys

I've created a `.env` file in the `backend` folder for you.

## Steps to Add Your Keys:

1. **Open the file**: `backend/.env`

2. **Find these two lines** (around lines 10-14):
   ```bash
   SECRET_KEY=PASTE_YOUR_GENERATED_SECRET_KEY_HERE
   CREDENTIAL_ENCRYPTION_KEY=PASTE_YOUR_GENERATED_CREDENTIAL_ENCRYPTION_KEY_HERE
   ```

3. **Replace the placeholder text** with your actual generated keys:
   ```bash
   SECRET_KEY=your-actual-secret-key-here
   CREDENTIAL_ENCRYPTION_KEY=your-actual-credential-encryption-key-here
   ```

## Example:

If your generated keys were:
- SECRET_KEY: `abc123xyz...` (43 characters)
- CREDENTIAL_ENCRYPTION_KEY: `def456uvw...` (44 characters)

Then your `.env` file should have:
```bash
SECRET_KEY=abc123xyz...
CREDENTIAL_ENCRYPTION_KEY=def456uvw...
```

## Important Notes:

1. **No quotes needed** - Just paste the key directly after the `=`
2. **No spaces** - Don't add spaces around the `=`
3. **One key per line** - Each key should be on its own line
4. **Keep it secure** - Never commit the `.env` file to git (it should be in `.gitignore`)

## Database URL:

If you're using **docker-compose**, the DATABASE_URL should be:
```bash
DATABASE_URL=postgresql://postgres:password@postgres:5432/troubleshooting_ai
```

If you're running **locally without docker**, use:
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/troubleshooting_ai
```

## After Adding Keys:

1. Save the `.env` file
2. Restart your backend service
3. The application should now start without security validation errors




