#!/usr/bin/env bash
# One-command discovery: download agent, install deps (venv), run scan.
# Usage:
#   curl -sSL "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/bootstrap.sh" | bash -s -- "https://dev.resolvify.tech/api/v1/tenant-admin/discovery/ingest" "YOUR_TOKEN"
# Or with repo file:
#   bash bootstrap.sh "https://.../ingest" "YOUR_TOKEN"
#
# Requires: curl, unzip, python3
set -e
INGEST_URL="${1:?Usage: bootstrap.sh INGEST_URL TOKEN}"
TOKEN="${2:?Usage: bootstrap.sh INGEST_URL TOKEN}"

# Derive base URL and agent.zip URL
if [[ "$INGEST_URL" == *"/api/"* ]]; then
  BASE_URL="${INGEST_URL%%/api/*}"
else
  BASE_URL="${INGEST_URL%/ingest}"
fi
AGENT_ZIP_URL="${BASE_URL}/api/v1/tenant-admin/discovery/agent.zip"

# Install dir: prefer ~/.resolvify-discovery so it persists
INSTALL_DIR="${RESOLVIFY_DISCOVERY_DIR:-$HOME/.resolvify-discovery}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "Downloading discovery agent from ${AGENT_ZIP_URL} ..."
TMPZIP=$(mktemp -t agent.zip.XXXXXX)
if ! curl -sfL "$AGENT_ZIP_URL" -o "$TMPZIP"; then
  echo "Download failed. If the server is behind a proxy or agent.zip is not available, copy the discovery-agent folder to this server and run: python3 discover.py \"$INGEST_URL\" \"TOKEN\"" >&2
  rm -f "$TMPZIP"
  exit 1
fi

# Check we got a zip (not HTML error page)
if ! unzip -l "$TMPZIP" >/dev/null 2>&1; then
  echo "Downloaded file is not a valid zip (server may have returned an error page). Copy discovery-agent folder manually and run: python3 discover.py \"$INGEST_URL\" \"TOKEN\"" >&2
  rm -f "$TMPZIP"
  exit 1
fi

echo "Extracting to $INSTALL_DIR ..."
# Extract; if zip has discovery-agent/ at root, we end up with discovery-agent/ inside INSTALL_DIR
unzip -o -q "$TMPZIP" -d "$INSTALL_DIR"
rm -f "$TMPZIP"

# Find discover.py (zip usually has discovery-agent/ at root)
if [[ -f "$INSTALL_DIR/discovery-agent/discover.py" ]]; then
  AGENT_DIR="$INSTALL_DIR/discovery-agent"
elif [[ -f "$INSTALL_DIR/discover.py" ]]; then
  AGENT_DIR="$INSTALL_DIR"
else
  AGENT_DIR="$INSTALL_DIR"
fi

if [[ ! -f "$AGENT_DIR/discover.py" ]]; then
  echo "Agent package layout unexpected. Looked for discover.py in $INSTALL_DIR" >&2
  exit 1
fi

echo "Installing dependencies and running discovery..."
cd "$AGENT_DIR"
exec python3 discover.py "$INGEST_URL" "$TOKEN"
