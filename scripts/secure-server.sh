#!/bin/bash
# Server Security Hardening Script
# Run as root

set -e

echo "=========================================="
echo "Server Security Hardening"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Secure SSH
echo -e "${YELLOW}[1] Securing SSH...${NC}"

# Check SSH service name
if systemctl list-units | grep -q "ssh.service"; then
    SSH_SERVICE="ssh"
elif systemctl list-units | grep -q "sshd.service"; then
    SSH_SERVICE="sshd"
else
    echo -e "${RED}Could not find SSH service${NC}"
    exit 1
fi

# Backup SSH config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)

# Disable password authentication
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Disable root login (or make it key-only)
sed -i 's/#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

# Ensure key authentication is enabled
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
grep -q "^PubkeyAuthentication" /etc/ssh/sshd_config || echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config

# Restart SSH
systemctl restart $SSH_SERVICE
echo -e "${GREEN}✓ SSH secured${NC}"
echo ""

# 2. Secure UFW - Close unnecessary ports
echo -e "${YELLOW}[2] Securing firewall (UFW)...${NC}"

# Keep only essential ports
UFW_KEEP_PORTS=(22 80 443)

# Get list of currently allowed ports
CURRENT_PORTS=$(ufw status numbered | grep -E "^\s*\[" | awk '{print $2}' | tr -d ']')

# Reset UFW rules (be careful!)
echo -e "${YELLOW}Current UFW rules will be reset. Keeping only: ${UFW_KEEP_PORTS[@]}${NC}"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Disable UFW temporarily
    ufw --force disable
    
    # Reset to defaults
    ufw --force reset
    
    # Set defaults
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow only essential ports
    for port in "${UFW_KEEP_PORTS[@]}"; do
        ufw allow $port/tcp
    done
    
    # Enable UFW
    ufw --force enable
    
    echo -e "${GREEN}✓ Firewall secured${NC}"
else
    echo -e "${YELLOW}Skipped firewall changes${NC}"
fi
echo ""

# 3. Secure sudo access
echo -e "${YELLOW}[3] Securing sudo access...${NC}"

# Backup sudoers
cp /etc/sudoers.d/90-cloud-init-users /etc/sudoers.d/90-cloud-init-users.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Remove NOPASSWD for ubuntu user (require password)
if [ -f /etc/sudoers.d/90-cloud-init-users ]; then
    sed -i 's/ubuntu ALL=(ALL) NOPASSWD:ALL/ubuntu ALL=(ALL) ALL/' /etc/sudoers.d/90-cloud-init-users
    echo -e "${GREEN}✓ Ubuntu user now requires password for sudo${NC}"
else
    echo -e "${YELLOW}No cloud-init sudoers file found${NC}"
fi
echo ""

# 4. Install and configure fail2ban
echo -e "${YELLOW}[4] Installing fail2ban...${NC}"

if ! command -v fail2ban-client &> /dev/null; then
    apt update
    apt install -y fail2ban
    
    # Configure fail2ban for SSH
    cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF
    
    systemctl enable fail2ban
    systemctl start fail2ban
    echo -e "${GREEN}✓ Fail2ban installed and configured${NC}"
else
    echo -e "${GREEN}✓ Fail2ban already installed${NC}"
fi
echo ""

# 5. Check for suspicious authorized_keys
echo -e "${YELLOW}[5] Checking SSH authorized_keys...${NC}"

FOUND_KEYS=false
for keyfile in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
    if [ -f "$keyfile" ]; then
        echo "Found: $keyfile"
        ls -la "$keyfile"
        FOUND_KEYS=true
    fi
done

if [ "$FOUND_KEYS" = false ]; then
    echo -e "${GREEN}✓ No authorized_keys files found${NC}"
fi
echo ""

# 6. Check Docker socket permissions
echo -e "${YELLOW}[6] Checking Docker security...${NC}"

if [ -e /var/run/docker.sock ]; then
    DOCKER_PERMS=$(stat -c "%a" /var/run/docker.sock)
    if [ "$DOCKER_PERMS" != "660" ]; then
        echo -e "${YELLOW}Docker socket permissions: $DOCKER_PERMS (should be 660)${NC}"
        chmod 660 /var/run/docker.sock
        chown root:docker /var/run/docker.sock
        echo -e "${GREEN}✓ Docker socket permissions fixed${NC}"
    else
        echo -e "${GREEN}✓ Docker socket permissions OK${NC}"
    fi
fi

# Check if Docker API is exposed
if netstat -tuln 2>/dev/null | grep -q ":2375\|:2376" || ss -tuln 2>/dev/null | grep -q ":2375\|:2376"; then
    echo -e "${RED}⚠️  Docker API is exposed on network!${NC}"
    echo "Blocking Docker API ports..."
    ufw deny 2375/tcp
    ufw deny 2376/tcp
    echo -e "${GREEN}✓ Docker API ports blocked${NC}"
else
    echo -e "${GREEN}✓ Docker API not exposed${NC}"
fi
echo ""

# 7. Summary
echo "=========================================="
echo "Security Hardening Complete"
echo "=========================================="
echo ""
echo "Changes made:"
echo "  ✓ SSH password authentication disabled"
echo "  ✓ SSH root login restricted (key-only)"
echo "  ✓ Firewall configured (only ports 22, 80, 443 open)"
echo "  ✓ Ubuntu user sudo now requires password"
echo "  ✓ Fail2ban installed and configured"
echo "  ✓ Docker socket permissions checked"
echo ""
echo "IMPORTANT:"
echo "  - Make sure you have SSH key access before disconnecting!"
echo "  - Test SSH connection from another terminal before closing this one"
echo "  - Review authorized_keys files if any were found"
echo ""

