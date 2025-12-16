# Security Hardening Guide - Immediate Action Required

## 🚨 Critical Situation: CVE-2025-55182 (React2Shell) Exploitation

Your VPS is being repeatedly compromised due to a vulnerability in your Next.js application. **Reimaging alone will NOT fix this** - the vulnerability must be patched first.

---

## ⚠️ Why Reimaging Alone Won't Work

1. **The vulnerability is in your application code**, not just the server
2. Attackers exploit the Next.js vulnerability to install malware
3. Even after cleanup, the vulnerable code remains
4. **You'll be compromised again within hours/days**

---

## ✅ Step-by-Step Recovery Plan

### **Phase 1: Patch Application (DO THIS FIRST - Before Reimaging)**

#### 1. Update Next.js to Latest Patched Version

```bash
cd frontend-nextjs
npm update next@latest
npm update eslint-config-next@latest
npm audit fix
```

#### 2. Review and Fix Security Issues

Your codebase has several critical vulnerabilities that need immediate attention:

**Critical (P0) - Fix Before Reimaging:**
- [ ] **MF-1**: Remove hardcoded `SECRET_KEY` in `backend/app/core/config.py`
- [ ] **MF-19**: Remove default database credentials
- [ ] **MF-2**: Fix SQL injection in vector store queries
- [ ] **MF-4**: Add command injection protection in infrastructure connectors
- [ ] **MF-7**: Remove credential encryption fallback (always require key)

**High Priority (P1) - Fix Before Production:**
- [ ] **MF-5**: Disable DEBUG mode by default
- [ ] **MF-6**: Restrict CORS to specific origins
- [ ] **MF-8**: Run Docker containers as non-root user (backend already has this)
- [ ] **MF-9**: Add WebSocket authentication
- [ ] **MF-10**: Add API rate limiting (already partially done)
- [ ] **MF-12**: Add file upload validation

#### 3. Commit and Push Patched Code

```bash
git add frontend-nextjs/package.json frontend-nextjs/package-lock.json
git commit -m "SECURITY: Update Next.js to patch CVE-2025-55182"
git push origin main
```

---

### **Phase 2: Reimage VPS (After Patching)**

**ONLY AFTER** you've patched the application:

1. **Backup essential data:**
   ```bash
   # Backup database
   docker compose -f docker-compose.production.yml exec postgres pg_dump -U postgres troubleshooting_ai > backup.sql
   
   # Backup environment files
   cp backend/.env backend/.env.backup
   ```

2. **Reimage the VPS** through Hostinger control panel

3. **Restore with patched code:**
   ```bash
   # Clone fresh repository
   git clone https://github.com/stiwari2004/bot.git
   cd bot
   
   # Restore environment
   cp backend/.env.backup backend/.env
   
   # Restore database
   docker compose -f docker-compose.production.yml up -d postgres
   docker compose -f docker-compose.production.yml exec postgres psql -U postgres troubleshooting_ai < backup.sql
   
   # Start services with patched code
   docker compose -f docker-compose.production.yml up -d --build
   ```

---

### **Phase 3: Implement Security Hardening**

#### 1. Firewall Configuration

```bash
# Install and configure UFW
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

#### 2. Fail2Ban for SSH Protection

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

#### 3. Disable Root Login via SSH

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Set:
PermitRootLogin no
PasswordAuthentication no  # Use SSH keys only

# Restart SSH
sudo systemctl restart sshd
```

#### 4. Nginx Security Headers

Add to your Nginx configs:

```nginx
# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

# Hide server version
server_tokens off;
```

#### 5. Rate Limiting in Nginx

Add to each server block:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

location /api {
    limit_req zone=api_limit burst=20 nodelay;
    # ... existing proxy_pass config
}

location /api/v1/auth/login {
    limit_req zone=login_limit burst=3 nodelay;
    # ... existing proxy_pass config
}
```

#### 6. Docker Security

- ✅ Backend already runs as non-root user
- Add to frontend Dockerfile:
  ```dockerfile
  RUN useradd -m -u 1000 appuser && \
      chown -R appuser:appuser /app
  USER appuser
  ```

#### 7. Environment Variable Security

- Never commit `.env` files
- Use strong, unique passwords
- Rotate secrets regularly
- Use environment-specific configs

#### 8. Monitoring and Alerts

```bash
# Install monitoring tools
sudo apt install logwatch
sudo apt install rkhunter
sudo apt install chkrootkit

# Schedule daily scans
sudo crontab -e
# Add: 0 2 * * * /usr/bin/rkhunter --check --skip-keypress
```

---

## 🔄 Ongoing Security Maintenance

### Weekly Tasks:
- [ ] Review application logs for suspicious activity
- [ ] Check for failed login attempts
- [ ] Review Docker container logs
- [ ] Check disk space (cryptominers can fill disks)

### Monthly Tasks:
- [ ] Update all dependencies: `npm audit fix` and `pip list --outdated`
- [ ] Review and rotate API keys and passwords
- [ ] Review firewall rules
- [ ] Check for security advisories for your stack

### Automated Monitoring:

Set up alerts for:
- Unusual CPU/memory usage (cryptominers)
- Unusual network traffic
- Failed authentication attempts
- New processes running as root
- Changes to system files

---

## 🤔 Should You Change VPS Providers?

**Short answer: Not necessary, but consider it if:**
- Hostinger doesn't provide adequate security support
- You need better DDoS protection
- You need managed security services

**However, the real issue is your application security**, not the provider. Even on AWS/Azure/GCP, a vulnerable application will be compromised.

**Better alternatives if switching:**
- **DigitalOcean**: Good security, clear documentation
- **Linode (Akamai)**: Strong security focus
- **Hetzner**: Good value, European data centers
- **AWS Lightsail**: Managed security features
- **Vultr**: Good security, global presence

---

## 📋 Quick Security Checklist

Before going live again:

- [ ] Next.js updated to latest version
- [ ] All P0 security fixes applied
- [ ] Firewall configured (UFW)
- [ ] Fail2Ban installed
- [ ] SSH root login disabled
- [ ] Strong passwords/keys for all services
- [ ] Nginx security headers added
- [ ] Rate limiting configured
- [ ] Docker containers run as non-root
- [ ] Environment variables secured
- [ ] Monitoring tools installed
- [ ] Regular backup schedule configured

---

## 🆘 If Compromised Again

1. **Immediately**: Stop all services
   ```bash
   docker compose -f docker-compose.production.yml down
   ```

2. **Check for backdoors:**
   ```bash
   # Check for suspicious processes
   ps aux | grep -E 'xmrig|miner|crypto|\.system'
   
   # Check for suspicious files
   find /tmp /var/tmp -type f -mtime -1
   
   # Check cron jobs
   crontab -l
   sudo crontab -l -u root
   ```

3. **Check systemd services:**
   ```bash
   systemctl list-units --type=service --state=running
   ```

4. **Review logs:**
   ```bash
   journalctl -u docker --since "24 hours ago"
   docker compose logs --tail=1000
   ```

5. **If found, document everything, then reimage**

---

## 📚 Resources

- [Next.js Security Best Practices](https://nextjs.org/docs/app/building-your-application/configuring/security-headers)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Nginx Security Headers](https://www.nginx.com/blog/http-strict-transport-security-hsts-and-nginx/)

---

**Remember: Security is an ongoing process, not a one-time fix.**

