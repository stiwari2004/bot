#!/usr/bin/env bash
# Obtain or force-renew Let's Encrypt certificate for resolvify.tech.
# Run on the server: sudo bash renew-ssl-resolvify.sh
#
# Set EMAIL before running, or pass as env: EMAIL=you@example.com sudo bash renew-ssl-resolvify.sh

set -e
EMAIL="${EMAIL:-}"
if [ -z "$EMAIL" ]; then
  echo "Set EMAIL (e.g. export EMAIL=you@example.com) then run again."
  exit 1
fi

echo "Obtaining new certificate for resolvify.tech and www.resolvify.tech..."
certbot certonly --nginx \
  -d resolvify.tech \
  -d www.resolvify.tech \
  --non-interactive --agree-tos \
  --email "$EMAIL"

echo "Reloading nginx..."
nginx -t && systemctl reload nginx
echo "Done. Certificate is at /etc/letsencrypt/live/resolvify.tech/"
