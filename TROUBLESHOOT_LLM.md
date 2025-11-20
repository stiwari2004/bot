# Troubleshooting LLM Empty Response Error

## Quick Diagnosis Steps

### Step 1: Check if Ollama is Running

**In PowerShell, run:**
```powershell
# Check if Ollama process is running
Get-Process -Name ollama -ErrorAction SilentlyContinue

# Test Ollama API directly
curl http://localhost:11434/api/tags
```

**Expected output:** Should show JSON with models list

**If it fails:**
- Start Ollama: `ollama serve`
- Or check Windows Services for "Ollama" service

---

### Step 2: Check if Models are Available

```powershell
# List available models
ollama list

# If no models, pull one:
ollama pull llama3.2
```

---

### Step 3: Test Ollama Chat Completion

```powershell
# Test with curl
curl http://localhost:11434/v1/chat/completions `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"model":"llama3.2","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

**Expected:** Should return JSON with a response

---

### Step 4: Check Docker Containers

```powershell
# Check if backend is running
docker-compose ps

# Check backend logs for LLM errors
docker-compose logs backend --tail=100 | Select-String -Pattern "LLM|ollama|empty"
```

---

### Step 5: Test Connection from Docker Container

```powershell
# Test if backend can reach Ollama
docker-compose exec backend curl -s http://host.docker.internal:11434/api/tags
```

**If this fails:**
- Ollama might not be accessible from Docker
- Check Windows Firewall settings
- Verify `host.docker.internal` resolves correctly

---

## Common Issues & Solutions

### Issue 1: Ollama Not Running
**Symptoms:** `curl http://localhost:11434/api/tags` fails

**Solution:**
```powershell
# Start Ollama service
ollama serve

# Or check Windows Services
services.msc
# Look for "Ollama" and start it
```

---

### Issue 2: No Models Available
**Symptoms:** `ollama list` shows no models

**Solution:**
```powershell
# Pull a model
ollama pull llama3.2

# Verify
ollama list
```

---

### Issue 3: Docker Can't Reach Ollama
**Symptoms:** Backend logs show connection errors

**Solution:**
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Check Windows Firewall - allow port 11434
3. Restart Docker containers:
   ```powershell
   docker-compose restart backend
   ```

---

### Issue 4: Empty Response from Ollama
**Symptoms:** Ollama responds but content is empty

**Possible causes:**
1. Model not fully loaded
2. Model name mismatch
3. Ollama configuration issue

**Solution:**
```powershell
# Check which model Ollama is using
curl http://localhost:11434/v1/models

# Try pulling the model again
ollama pull llama3.2

# Restart Ollama
# Stop: Get-Process ollama | Stop-Process
# Start: ollama serve
```

---

### Issue 5: Model Name Mismatch
**Symptoms:** Backend tries to use wrong model name

**Check:**
1. What model is available: `ollama list`
2. What backend expects: Check `docker-compose.yml` for `LLAMACPP_MODEL_ID`
3. Update if needed or ensure model name matches

---

## Quick Fix Commands

**If nothing works, try this sequence:**

```powershell
# 1. Stop everything
docker-compose down
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process

# 2. Start Ollama
ollama serve

# 3. Verify Ollama
curl http://localhost:11434/api/tags

# 4. Pull model if needed
ollama pull llama3.2

# 5. Start Docker
docker-compose up -d

# 6. Check backend logs
docker-compose logs backend --tail=50
```

---

## Verify Everything is Working

**Test the full chain:**

1. **Ollama on host:**
   ```powershell
   curl http://localhost:11434/v1/chat/completions -Method POST -ContentType "application/json" -Body '{"model":"llama3.2","messages":[{"role":"user","content":"Hi"}],"max_tokens":5}'
   ```

2. **Backend can reach Ollama:**
   ```powershell
   docker-compose exec backend curl -s http://host.docker.internal:11434/v1/models
   ```

3. **Backend logs show successful LLM calls:**
   ```powershell
   docker-compose logs backend | Select-String -Pattern "LLM.*200|chat.*completion"
   ```

---

## Still Having Issues?

Check the backend logs for specific error messages:
```powershell
docker-compose logs backend --tail=200 | Select-String -Pattern "LLM|error|empty|non-200" -Context 3
```

This will show you exactly what error the backend is seeing when trying to connect to Ollama.



