# Ollama Setup Guide - Llama 3.2

This guide will help you set up Ollama with Llama 3.2 for your containerized AI troubleshooting system.

## Why Ollama?

✅ **Much simpler** than llama.cpp - just install and run!  
✅ **Automatic model management** - no manual downloads  
✅ **OpenAI-compatible API** - works seamlessly with existing code  
✅ **GPU acceleration** - automatically uses your NVIDIA GPU  
✅ **Easy updates** - simple `ollama pull` commands  

---

## Step 1: Install Ollama

### Option A: Use the Installer Script
```powershell
cd C:\Users\Admin\Documents\bot
.\install-ollama.ps1
```

### Option B: Manual Installation
1. **Download Ollama:**
   - Visit: https://ollama.com/download/windows
   - Download the Windows installer
   - Run `OllamaSetup.exe`

2. **Or use winget:**
   ```powershell
   winget install Ollama.Ollama
   ```

3. **Verify Installation:**
   ```powershell
   ollama --version
   ```

Ollama will automatically start as a Windows service after installation.

---

## Step 2: Pull Llama 3.2 Model

Ollama makes this super easy - just one command!

```powershell
ollama pull llama3.2:8b
```

**Model Options:**
- `llama3.2:8b` - **Recommended** - Best balance (4.7GB, ~8GB RAM)
- `llama3.2:3b` - Smaller, faster (2.0GB, ~4GB RAM)
- `llama3.2:70b` - Largest, best quality (40GB, ~80GB RAM) - *Too large for 32GB system*

**With 32GB RAM, you can also try:**
- `llama3.2:8b` - Default recommendation
- `llama3.1:8b` - Alternative if 3.2 has issues
- `mistral:7b` - Excellent alternative model

The download will take 10-30 minutes depending on your internet speed.

---

## Step 3: Start Ollama Server

Ollama usually runs automatically as a Windows service, but you can verify:

```powershell
# Check if running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

Or use our helper script:
```powershell
.\start-ollama.ps1
```

This script will:
- ✅ Check if Ollama is installed
- ✅ Verify server is running
- ✅ Pull Llama 3.2 if not already installed
- ✅ Configure everything automatically

---

## Step 4: Update Docker Configuration

The `docker-compose.yml` has been updated to use Ollama's port (11434).

**Verify the configuration:**
```yaml
LLAMACPP_BASE_URL=http://host.docker.internal:11434
```

This allows Docker containers to access Ollama running on your host machine.

---

## Step 5: Start Docker Containers

```powershell
cd C:\Users\Admin\Documents\bot
docker-compose up -d
```

This starts:
- PostgreSQL (database)
- Redis (caching)
- Backend API (port 8000) - **now connects to Ollama**
- Frontend (port 3000)
- Worker (background tasks)

---

## Step 6: Verify Everything Works

**1. Check Ollama is running:**
```powershell
curl http://localhost:11434/api/tags
```

**2. Test Ollama API:**
```powershell
curl http://localhost:11434/v1/models
```

**3. Check Backend:**
```powershell
curl http://localhost:8000/health
```

**4. Test LLM Connection:**
```powershell
python test_llm_connection.py
```

**5. Open Frontend:**
- Browser: http://localhost:3000

---

## Daily Usage

**To start the system:**

1. **Ollama** - Usually runs automatically as a service. If not:
   ```powershell
   ollama serve
   ```

2. **Docker Containers:**
   ```powershell
   docker-compose up -d
   ```

**To stop the system:**

1. **Stop Docker:**
   ```powershell
   docker-compose down
   ```

2. **Ollama** - Leave running (it's lightweight)

---

## Troubleshooting

### Ollama Not Starting
- Check Windows Services: `services.msc`
- Look for "Ollama" service and start it
- Or run `ollama serve` manually

### Docker Can't Connect to Ollama
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check Windows Firewall isn't blocking port 11434
- Verify `host.docker.internal` resolves correctly

### Model Not Found
- Pull the model: `ollama pull llama3.2:8b`
- List installed models: `ollama list`
- Check model name matches exactly

### Out of Memory
- Use smaller model: `ollama pull llama3.2:3b`
- Close other applications
- Reduce Docker memory allocation

### GPU Not Working
- Ollama automatically detects and uses GPU
- Check NVIDIA drivers are up to date
- Verify GPU is detected: `ollama ps` (shows GPU usage)

---

## Ollama Commands Reference

```powershell
# List installed models
ollama list

# Pull a model
ollama pull llama3.2:8b

# Run a model interactively
ollama run llama3.2:8b

# Show running models
ollama ps

# Remove a model
ollama rm llama3.2:8b

# Start server
ollama serve
```

---

## Model Recommendations for 32GB RAM

| Model | Size | RAM Usage | Quality | Speed | Recommendation |
|-------|------|-----------|---------|-------|----------------|
| llama3.2:8b | 4.7GB | ~8GB | ⭐⭐⭐⭐⭐ | Fast | ✅ **Best choice** |
| llama3.2:3b | 2.0GB | ~4GB | ⭐⭐⭐⭐ | Very Fast | Good for testing |
| mistral:7b | 4.1GB | ~8GB | ⭐⭐⭐⭐⭐ | Fast | Excellent alternative |
| llama3.1:8b | 4.7GB | ~8GB | ⭐⭐⭐⭐ | Fast | If 3.2 has issues |

**Recommendation:** Start with **llama3.2:8b** - it's the latest and best quality.

---

## Advantages Over llama.cpp

✅ **Simpler Setup** - No manual compilation or binary management  
✅ **Automatic Updates** - Easy model updates with `ollama pull`  
✅ **Better GPU Support** - Automatic GPU detection and usage  
✅ **Model Management** - Built-in model versioning and management  
✅ **Community Models** - Access to many pre-configured models  
✅ **Active Development** - Regular updates and improvements  

---

## Next Steps

1. ✅ Install Ollama
2. ✅ Pull Llama 3.2: `ollama pull llama3.2:8b`
3. ✅ Verify Ollama is running
4. ✅ Start Docker containers
5. ✅ Test the system

Enjoy your simplified LLM setup! 🚀






