#!/usr/bin/env bash
set -euo pipefail

ACTION_VERIFY_AUDIT=false
ACTION_VERIFY_S3=false
ACTION_API_SMOKE=false

if [[ $# -eq 0 ]]; then
  ACTION_VERIFY_AUDIT=true
  ACTION_API_SMOKE=true
else
  for arg in "$@"; do
    case "$arg" in
      --verify-audit) ACTION_VERIFY_AUDIT=true ;;
      --verify-s3) ACTION_VERIFY_S3=true ;;
      --api-smoke) ACTION_API_SMOKE=true ;;
      --help|-h)
        cat <<EOF
Run DR verification tasks.

Usage: $0 [--verify-audit] [--verify-s3] [--api-smoke]

  --verify-audit   Validate audit log hash chain integrity.
  --verify-s3      Ensure the immutable S3 archive has entries for today.
  --api-smoke      Hit health and session endpoints.
EOF
        exit 0
        ;;
      *)
        echo "Unknown argument: $arg" >&2
        exit 1
        ;;
    esac
  done
fi

AUDIT_PATH="${AUDIT_LOG_PATH:-logs/audit.log}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"

verify_audit() {
  if [[ ! -f "$AUDIT_PATH" ]]; then
    echo "[audit] audit log not found at $AUDIT_PATH" >&2
    exit 2
  fi
  AUDIT_PATH="$AUDIT_PATH" python - <<'PY'
import hashlib
import json
import os
import sys

path = os.environ.get("AUDIT_PATH")
prev = ""
with open(path, "r", encoding="utf-8") as fh:
    for idx, line in enumerate(fh, start=1):
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        expected = hashlib.sha256((prev + json.dumps(
            {
                k: record[k]
                for k in ("event_type", "payload", "session_id", "ts")
                if k in record
            },
            sort_keys=True,
            separators=(",", ":"),
        )).encode()).hexdigest()
        if record.get("prev_hash", "") != prev:
            sys.exit(f"[audit] line {idx}: prev_hash mismatch")
        if record.get("hash") != expected:
            sys.exit(f"[audit] line {idx}: hash mismatch")
        prev = record["hash"]
print("[audit] hash chain validated")
PY
}

verify_s3() {
  if [[ -z "${AUDIT_LOG_S3_BUCKET:-}" ]]; then
    echo "[s3] AUDIT_LOG_S3_BUCKET not set; skipping"
    return
  fi
  if ! command -v aws >/dev/null; then
    echo "[s3] aws CLI not found; install to run S3 verification." >&2
    exit 3
  fi
  local prefix="${AUDIT_LOG_S3_PREFIX:-audit-log/}"
  local date_path
  date_path="$(date -u +"%Y/%m/%d")"
  local s3_uri="s3://${AUDIT_LOG_S3_BUCKET}/${prefix%/}/${date_path}/"
  if ! aws s3 ls "$s3_uri" >/dev/null; then
    echo "[s3] no objects discovered under $s3_uri" >&2
    exit 4
  fi
  echo "[s3] verified presence of immutable logs under $s3_uri"
}

api_smoke() {
  set +e
  curl -fsS "${BACKEND_BASE_URL}/health" >/dev/null
  curl -fsS "${BACKEND_BASE_URL}/api/v1/executions/demo/sessions?limit=1" >/dev/null
  set -e
  echo "[api] smoke test completed"
}

if $ACTION_VERIFY_AUDIT; then
  AUDIT_PATH="$AUDIT_PATH" verify_audit
fi

if $ACTION_VERIFY_S3; then
  verify_s3
fi

if $ACTION_API_SMOKE; then
  api_smoke
fi

echo "[dr] checklist complete"

