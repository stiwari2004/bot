#!/bin/bash

# SolarWinds Agent Installation Script for Ubuntu x86_64
# This script downloads and installs the SolarWinds UAMS client

set -e  # Exit on error

# Environment variables
export UAMS_ACCESS_TOKEN="SJlOm5IXKD85fZsr4HWrONg5GasbunM4QDPGMq7YtUWW_0IuPYQLap26YhrctBYpmhBrfuI"
export UAMS_METADATA="role:host-monitoring,installationSessionId:6d064398-5651-48dd-8810-0f228eefa5da"
export SWO_URL="ap-01.cloud.solarwinds.com"

# Check architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

if [ "$ARCH" != "x86_64" ]; then
    echo "Warning: Expected x86_64, but detected $ARCH"
fi

# Package name for x86_64
PACKAGE="uamsclient-x86_64.deb"
TEMP_DIR="/tmp/solarwinds-install"

# Create temp directory
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "=========================================="
echo "SolarWinds Agent Installation"
echo "=========================================="
echo "SWO URL: $SWO_URL"
echo "Package: $PACKAGE"
echo "=========================================="

# Check if package already exists
if [ -f "$PACKAGE" ]; then
    echo "Found existing package: $PACKAGE"
else
    echo "Downloading SolarWinds agent..."
    echo ""
    echo "NOTE: You need to download the agent from SolarWinds portal:"
    echo "1. Go to: https://$SWO_URL"
    echo "2. Navigate to: Settings > Agents > Add Agent"
    echo "3. Select: Linux > x86_64"
    echo "4. Download the .deb file"
    echo ""
    echo "OR use the direct download URL if available:"
    echo ""
    
    # Try to download from common SolarWinds URLs
    DOWNLOAD_URLS=(
        "https://$SWO_URL/uamsclient-x86_64.deb"
        "https://downloads.solarwinds.com/solarwinds/Download.aspx?FilePath=/UAMS/uamsclient-x86_64.deb"
    )
    
    DOWNLOADED=0
    for URL in "${DOWNLOAD_URLS[@]}"; do
        echo "Trying: $URL"
        if wget --no-check-certificate -O "$PACKAGE" "$URL" 2>/dev/null; then
            echo "✓ Successfully downloaded from: $URL"
            DOWNLOADED=1
            break
        fi
    done
    
    if [ $DOWNLOADED -eq 0 ]; then
        echo ""
        echo "❌ Automatic download failed."
        echo ""
        echo "Please download manually:"
        echo "1. Visit: https://$SWO_URL"
        echo "2. Go to Settings > Agents > Add Agent"
        echo "3. Select Linux > x86_64"
        echo "4. Download the .deb file"
        echo "5. Transfer it to this server"
        echo "6. Place it in: $TEMP_DIR/$PACKAGE"
        echo ""
        echo "Then run this script again."
        exit 1
    fi
fi

# Verify package exists
if [ ! -f "$PACKAGE" ]; then
    echo "❌ Error: Package file not found: $PACKAGE"
    exit 1
fi

echo ""
echo "Installing package: $PACKAGE"
echo ""

# Install the package
sudo dpkg -i "$PACKAGE" || {
    echo "Fixing dependencies..."
    sudo apt-get update
    sudo apt-get install -f -y
}

# Verify installation
if systemctl is-active --quiet uamsclient 2>/dev/null || service uamsclient status >/dev/null 2>&1; then
    echo ""
    echo "✓ SolarWinds agent installed successfully!"
    echo ""
    echo "Service status:"
    systemctl status uamsclient 2>/dev/null || service uamsclient status 2>/dev/null || echo "Service status check unavailable"
else
    echo ""
    echo "⚠ Installation completed, but service status could not be verified."
    echo "Check manually with: sudo systemctl status uamsclient"
fi

echo ""
echo "=========================================="
echo "Installation Complete"
echo "=========================================="
echo ""
echo "Environment variables set:"
echo "  UAMS_ACCESS_TOKEN: ${UAMS_ACCESS_TOKEN:0:20}..."
echo "  UAMS_METADATA: $UAMS_METADATA"
echo "  SWO_URL: $SWO_URL"
echo ""
echo "To check agent status:"
echo "  sudo systemctl status uamsclient"
echo ""
echo "To view agent logs:"
echo "  sudo journalctl -u uamsclient -f"
echo ""

