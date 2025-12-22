# Security Hardening Guide - Prevent Malware Reinfection

## Root Cause Analysis

If malware keeps coming back after reimaging, the infection vector is likely one of these:

1. **Weak SSH credentials** (password or key-based)
2. **Exposed services** (web apps, databases, Docker APIs)
3. **Compromised Docker images** or containers
4. **Vulnerable application code** (SQL injection, RCE, etc.)
5. **Compromised user accounts** with sudo access
6. **Backdoors in application code** or configuration files

## Immediate Security Hardening Steps

### 1. Secure SSH Access

```bash
# Disable password authentication (use keys only)
sudo nano /etc/ssh/sshd_config
# Set:
# PasswordAuthentication no
# PermitRootLogin no  # Or use PermitRootLogin prohibit-password
# PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart sshd

# Check for weak SSH keys
find /home -name "authorized_keys" -exec ls -la {} \;
find /root -name "authorized_keys" -exec ls -la {} \;

# Remove any suspicious authorized_keys entries
```

### 2. Audit User Accounts

```bash
# Check all users with shell access
cat /etc/passwd | grep -E "/bin/(bash|sh)$"

# Check users with sudo access
grep -E "^[^#].*ALL.*NOPASSWD" /etc/sudoers
grep -E "^[^#].*ALL.*NOPASSWD" /etc/sudoers.d/*

# Check for suspicious users
awk -F: '$3 == 0 {print $1}' /etc/passwd  # Users with UID 0
```

### 3. Secure Docker

```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# If world-writable, fix it:
sudo chmod 660 /var/run/docker.sock
sudo chown root:docker /var/run/docker.sock

# Disable Docker API if exposed
# Check if Docker API is listening:
netstat -tuln | grep 2375 || ss -tuln | grep 2375

# If found, disable it in /etc/docker/daemon.json:
# {
#   "hosts": ["unix:///var/run/docker.sock"]
# }
```

### 4. Scan for Backdoors in Code

```bash
# Check for suspicious code patterns
cd /home/opsbot/bot

# Look for base64 encoded strings (common in backdoors)
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.js" \) -exec grep -l "base64\|eval\|exec\|system\|subprocess" {} \;

# Check for suspicious network connections in code
grep -r "curl.*http\|wget.*http\|nc.*-e\|bash.*-i" --include="*.sh" --include="*.py" .

# Check for hardcoded credentials
grep -r "password.*=\|PASSWORD.*=\|secret.*=\|SECRET.*=" --include="*.py" --include="*.js" --include="*.env" . | grep -v ".git"

# Check Docker images for vulnerabilities
docker images
docker scan <image_name>  # If Docker Scout is available
```

### 5. Firewall Configuration

```bash
# Install and configure UFW (if not already installed)
sudo apt update
sudo apt install ufw -y

# Deny all incoming by default
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Enable firewall
sudo ufw enable
sudo ufw status verbose

# Block Docker API if exposed
sudo ufw deny 2375/tcp
sudo ufw deny 2376/tcp
```

### 6. Application Security

```bash
# Check for exposed environment variables
docker compose -f docker-compose.production.yml config | grep -i "password\|secret\|key\|token"

# Review application logs for suspicious activity
docker compose -f docker-compose.production.yml logs backend --tail=1000 | grep -iE "error|exception|unauthorized|forbidden|injection"

# Check database for suspicious data
docker compose -f docker-compose.production.yml exec -T postgres psql -U postgres -d troubleshooting_ai -c "SELECT * FROM users WHERE role = 'super_admin';"
```

### 7. Monitor for Intrusions

```bash
# Install fail2ban to prevent brute force attacks
sudo apt install fail2ban -y

# Configure fail2ban for SSH
sudo nano /etc/fail2ban/jail.local
# Add:
# [sshd]
# enabled = true
# port = 22
# filter = sshd
# logpath = /var/log/auth.log
# maxretry = 3
# bantime = 3600

sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check fail2ban status
sudo fail2ban-client status sshd
```

### 8. Regular Security Audits

```bash
# Create a security audit script
cat > /root/security-audit.sh << 'EOF'
#!/bin/bash
echo "=== Security Audit ==="
echo "Date: $(date)"
echo ""

echo "[1] Failed login attempts:"
grep "Failed password" /var/log/auth.log | tail -20

echo ""
echo "[2] Successful SSH logins:"
grep "Accepted" /var/log/auth.log | tail -20

echo ""
echo "[3] Suspicious processes:"
ps aux | grep -iE "xmrig|miner|crypto|\.system|4thepool|watcher" | grep -v grep

echo ""
echo "[4] Network connections:"
netstat -tuln | grep LISTEN || ss -tuln | grep LISTEN

echo ""
echo "[5] Docker containers:"
docker ps -a

echo ""
echo "[6] Disk usage:"
df -h

echo ""
echo "[7] Recent file changes in /tmp:"
find /tmp -type f -mtime -1 -ls 2>/dev/null | head -20
EOF

chmod +x /root/security-audit.sh

# Schedule daily audit
echo "0 2 * * * /root/security-audit.sh >> /var/log/security-audit.log 2>&1" | sudo crontab -
```

### 9. Application-Level Security

```bash
# Review your application code for:
# - SQL injection vulnerabilities
# - Command injection (os.system, subprocess with user input)
# - File upload vulnerabilities
# - Authentication bypasses
# - Hardcoded credentials

# Check backend code
cd /home/opsbot/bot/backend
grep -r "os.system\|subprocess\|eval\|exec" --include="*.py" . | grep -v "__pycache__"

# Check for SQL injection risks
grep -r "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" --include="*.py" .
```

### 10. Docker Security Best Practices

```bash
# Run containers as non-root user
# Update docker-compose.production.yml to include:
# services:
#   backend:
#     user: "1000:1000"  # Non-root user

# Scan Docker images regularly
docker images | grep -v REPOSITORY | awk '{print $1}' | xargs -I {} docker scan {}

# Use specific image tags (not :latest)
# Update docker-compose.production.yml to use specific versions

# Limit container resources
# Add to docker-compose.production.yml:
# services:
#   backend:
#     deploy:
#       resources:
#         limits:
#           cpus: '2'
#           memory: 2G
```

## Prevention Checklist

- [ ] SSH password authentication disabled
- [ ] SSH root login disabled (or key-only)
- [ ] Firewall (UFW) enabled and configured
- [ ] Fail2ban installed and configured
- [ ] Docker socket permissions secured
- [ ] Docker API not exposed to network
- [ ] All user accounts audited
- [ ] Application code scanned for vulnerabilities
- [ ] Environment variables secured (no hardcoded secrets)
- [ ] Regular security audits scheduled
- [ ] Log monitoring enabled
- [ ] Containers run as non-root users
- [ ] Docker images use specific tags (not :latest)

## Ongoing Monitoring

1. **Set up log monitoring** - Use tools like `logwatch` or `rsyslog` to monitor system logs
2. **Regular security audits** - Run the audit script daily
3. **Update regularly** - Keep system and Docker images updated
4. **Monitor resource usage** - Unusual CPU/memory spikes can indicate malware
5. **Review application logs** - Check for suspicious API calls or errors

## If Malware is Found Again

1. **Immediately disconnect from network** (if possible)
2. **Run detection script**: `./scripts/detect-malware.sh`
3. **Run removal script**: `./scripts/remove-malware.sh`
4. **Identify infection vector** - Check logs around the time of infection
5. **Patch the vulnerability** - Fix the security hole that allowed infection
6. **Change all credentials** - SSH keys, database passwords, API keys
7. **Reimage if necessary** - If backdoor is too deep, reimage again

## Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Linux Server Hardening](https://www.cyberciti.biz/tips/linux-security.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
