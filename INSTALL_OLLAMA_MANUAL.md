# Manual Ollama Installation Guide

Since PowerShell scripts are restricted, here's how to install Ollama manually:

## Step 1: Download Ollama

The download page should have opened in your browser. If not:
- Visit: https://ollama.com/download/windows
- Click "Download for Windows"
- Save the installer

## Step 2: Install Ollama

1. Run the downloaded `OllamaSetup.exe`
2. Follow the installation wizard
3. Ollama will automatically start as a Windows service after installation

## Step 3: Verify Installation

Open a **new** PowerShell window and run:

```powershell
ollama --version
```

If you see a version number, Ollama is installed! ✅

## Step 4: Pull Llama 3.2

```powershell
ollama pull llama3.2:8b
```

This will download ~4.7GB and take 10-30 minutes depending on your internet speed.

## Step 5: Verify It's Working

```powershell
# List installed models
ollama list

# Test the model
ollama run llama3.2:8b
```

Type a question and press Enter. Type `/bye` to exit.

## Alternative: Use winget (if available)

If you have Windows Package Manager (winget) installed:

```powershell
winget install Ollama.Ollama
```

Then proceed to Step 4.

---

## After Installation

Once Ollama is installed, you can:

1. **Start Docker containers:**
   ```powershell
   docker-compose up -d
   ```

2. **Verify Ollama is accessible:**
   ```powershell
   curl http://localhost:11434/api/tags
   ```

3. **Test the full system:**
   - Backend: http://localhost:8000/health
   - Frontend: http://localhost:3000

---

## Troubleshooting

**"ollama not recognized" after installation:**
- Close and reopen PowerShell (to refresh PATH)
- Or restart your computer
- Check if Ollama service is running: `services.msc` → look for "Ollama"

**Ollama service not running:**
- Open Services: `services.msc`
- Find "Ollama" service
- Right-click → Start

**Can't download model:**
- Check internet connection
- Try: `ollama pull llama3.2:8b` again
- Check available disk space (need ~5GB free)

---

That's it! Ollama is much simpler than llama.cpp - no compilation or manual model management needed! 🚀






