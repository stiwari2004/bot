# Quick Start Guide - Ollama + Llama 3.2

Follow these steps to get your system running with Ollama:

## 1. Install Docker Desktop (5-10 minutes)

**Option A: Use the download script:**
```powershell
cd C:\Users\Admin\Documents\bot
.\download-docker.ps1
```

**Option B: Download manually:**
1. Visit: https://www.docker.com/products/docker-desktop/
2. Download "Docker Desktop for Windows"
3. Run the installer
4. Enable WSL 2 backend
5. Restart if prompted
6. Launch Docker Desktop

**Verify:**
```powershell
docker --version
```

---

## 2. Install Ollama (2 minutes)

**Option A: Use the installer script:**
```powershell
cd C:\Users\Admin\Documents\bot
.\install-ollama.ps1
```

**Option B: Manual installation:**
1. Visit: https://ollama.com/download/windows
2. Download and run the installer
3. Ollama will start automatically as a service

**Or use winget:**
```powershell
winget install Ollama.Ollama
```

**Verify:**
```powershell
ollama --version
```

---

## 3. Pull Llama 3.2 Model (10-30 minutes)

This is super easy with Ollama - just one command!

```powershell
ollama pull llama3.2:8b
```

**Or use our helper script (does everything):**
```powershell
.\start-ollama.ps1
```

This will:
- ✅ Check if Ollama is installed
- ✅ Verify server is running
- ✅ Pull Llama 3.2:8b if not already installed
- ✅ Configure everything automatically

**Model size:** ~4.7GB download, ~8GB RAM usage

---

## 4. Start Docker Containers

```powershell
cd C:\Users\Admin\Documents\bot
docker-compose up -d
```

This starts all services:
- PostgreSQL (database)
- Redis (caching)
- Backend API (port 8000) - **connects to Ollama**
- Frontend (port 3000)
- Worker (background tasks)

---

## 5. Verify Everything Works

**Check Ollama:**
```powershell
curl http://localhost:11434/api/tags
```

**Check Backend:**
```powershell
curl http://localhost:8000/health
```

**Open Frontend:**
- Browser: http://localhost:3000

**Test LLM Connection:**
```powershell
python test_llm_connection.py
```

---

## Daily Usage

**To start the system:**

1. **Ollama** - Usually runs automatically. If not:
   ```powershell
   ollama serve
   ```

2. **Docker:**
   ```powershell
   docker-compose up -d
   ```

**To stop the system:**

1. **Stop Docker:**
   ```powershell
   docker-compose down
   ```

2. **Ollama** - Leave running (it's lightweight and runs as a service)

---

## Why Ollama is Better

✅ **Much simpler** - No manual model downloads or compilation  
✅ **Automatic GPU** - Detects and uses your NVIDIA GPU automatically  
✅ **Easy updates** - `ollama pull llama3.2:8b` to update  
✅ **OpenAI-compatible** - Works seamlessly with existing code  
✅ **Better management** - Built-in model versioning  

---

## Troubleshooting

**Ollama not found:**
- Make sure Ollama is installed: `ollama --version`
- Check Windows Services for "Ollama" service

**Model not found:**
- Pull the model: `ollama pull llama3.2:8b`
- List models: `ollama list`

**Docker can't connect:**
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check Windows Firewall settings

**Port 11434 in use:**
- Ollama uses port 11434 by default
- Check what's using it: `netstat -ano | findstr :11434`

---

## Need More Help?

See `OLLAMA_SETUP_GUIDE.md` for detailed instructions and troubleshooting.






