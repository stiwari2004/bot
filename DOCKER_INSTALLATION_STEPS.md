# Docker Desktop Installation Steps

Docker Desktop needs to be installed before we can start the containers.

## Step 1: Download Docker Desktop

The download page should have opened in your browser. If not:
- Visit: https://www.docker.com/products/docker-desktop/
- Click "Download for Windows"
- Save the installer (`Docker Desktop Installer.exe`)

## Step 2: Install Docker Desktop

1. **Run the installer:**
   - Double-click `Docker Desktop Installer.exe`
   - Follow the installation wizard

2. **Important settings during installation:**
   - ✅ Enable "Use WSL 2 instead of Hyper-V" (recommended)
   - ✅ Add shortcut to desktop (optional)

3. **After installation:**
   - You may be prompted to restart your computer
   - **Restart if prompted** - this is required for WSL 2

4. **Launch Docker Desktop:**
   - After restart, launch Docker Desktop from Start Menu
   - Wait for it to start (whale icon in system tray)
   - First launch may take a few minutes to initialize

## Step 3: Verify Installation

Open a **new** PowerShell window and run:

```powershell
docker --version
docker-compose --version
```

You should see version numbers. ✅

## Step 4: Configure Docker Resources

1. **Open Docker Desktop**
2. **Go to Settings** (gear icon)
3. **Resources tab:**
   - **Memory:** Set to **16GB** (you have 32GB, so this is safe)
   - **CPUs:** Use 50-75% of available cores
   - **Disk:** Leave default or increase if needed
4. **Click "Apply & Restart"**

## Step 5: Start Your Containers

Once Docker Desktop is running:

```powershell
cd C:\Users\Admin\Documents\bot
docker-compose up -d
```

This will start:
- PostgreSQL (database)
- Redis (caching)
- Backend API (port 8000)
- Frontend (port 3000)
- Worker (background tasks)

## Step 6: Verify Everything is Running

```powershell
# Check running containers
docker ps

# Check backend health
curl http://localhost:8000/health

# Open frontend in browser
# http://localhost:3000
```

## Troubleshooting

**Docker Desktop won't start:**
- Ensure WSL 2 is installed: `wsl --install`
- Check Windows Features: Enable "Virtual Machine Platform" and "Windows Subsystem for Linux"
- Restart computer

**"docker not recognized" after installation:**
- Close and reopen PowerShell (to refresh PATH)
- Or restart your computer
- Check Docker Desktop is running (whale icon in system tray)

**Out of memory errors:**
- Reduce Docker memory allocation in Settings
- Close other applications
- Ensure you have enough free RAM

**Port conflicts:**
- Check if ports 5432, 6379, 8000, 3000 are in use
- Stop conflicting services or change ports in docker-compose.yml

---

## Quick Checklist

- [ ] Docker Desktop downloaded
- [ ] Docker Desktop installed
- [ ] Computer restarted (if prompted)
- [ ] Docker Desktop launched and running
- [ ] Docker resources configured (16GB RAM)
- [ ] `docker --version` works
- [ ] `docker-compose --version` works
- [ ] Ready to run `docker-compose up -d`

---

Once Docker Desktop is installed and running, we can start your containers! 🚀




