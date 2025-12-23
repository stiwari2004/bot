cat > /root/one_shot_miner_cleanup.sh <<'BASH'
#!/usr/bin/env bash
set -Eeuo pipefail

# One-shot crypto-miner cleanup & persistence neutralizer (Ubuntu)
# Logs everything to /root/ir-<timestamp>/
# Usage:
#   bash /root/one_shot_miner_cleanup.sh
# Optional:
#   DRY_RUN=1 bash /root/one_shot_miner_cleanup.sh   # no changes, just report

DRY_RUN="${DRY_RUN:-0}"
TS="$(date +%F_%H%M%S)"
OUT="/root/ir-${TS}"
LOG="${OUT}/run.log"
mkdir -p "$OUT"

exec > >(tee -a "$LOG") 2>&1

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY-RUN] $*"
  else
    echo "[RUN] $*"
    eval "$@"
  fi
}

echo "============================================================"
echo " One-shot Miner Cleanup  |  $(date)  |  DRY_RUN=${DRY_RUN}"
echo " Output: ${OUT}"
echo "============================================================"
echo

echo "[1] Baseline system context"
uname -a | tee "${OUT}/uname.txt"
uptime | tee "${OUT}/uptime.txt"
id | tee "${OUT}/id.txt"
echo

echo "[2] Capture suspicious process snapshot"
ps auxwwf | tee "${OUT}/ps_full.txt"
ps auxwwf | egrep -i "xmrig|minerd|miner|crypto|watcher|systemhelper|syshelper|kdevtmpfsi|kinsing|netns|java-updater|xm|rig|pm2|node" \
  | tee "${OUT}/ps_suspicious.txt" || true
echo

echo "[3] Capture network + listening sockets"
ss -tulpn | tee "${OUT}/ss_tulpn.txt" || true
ss -tpna | tee "${OUT}/ss_tpna.txt" || true
echo

echo "[4] Capture systemd units/timers that look suspicious"
systemctl list-unit-files --no-pager | tee "${OUT}/systemd_unit_files.txt"
systemctl list-units --type=service --all --no-pager | tee "${OUT}/systemd_services_all.txt"
systemctl list-timers --all --no-pager | tee "${OUT}/systemd_timers_all.txt"
echo

echo "[5] Search persistence locations (systemd/cron/rc.local/profile)"
# systemd custom units
grep -RIn --binary-files=without-match -E "pm2|node|xmrig|wget|curl|45\.156\.24\.168|rplant|mining|stratum" \
  /etc/systemd/system /lib/systemd/system /usr/lib/systemd/system 2>/dev/null \
  | tee "${OUT}/grep_systemd_persistence.txt" || true

# cron
for p in /etc/cron* /var/spool/cron /var/spool/cron/crontabs; do
  [[ -e "$p" ]] || continue
  grep -RIn --binary-files=without-match -E "pm2|node|xmrig|wget|curl|45\.156\.24\.168|rplant|mining|stratum" \
    "$p" 2>/dev/null | tee -a "${OUT}/grep_cron_persistence.txt" || true
done

# rc.local & profiles
for f in /etc/rc.local /etc/profile /etc/bash.bashrc /root/.bashrc /root/.profile; do
  [[ -f "$f" ]] || continue
  grep -nE "pm2|node|xmrig|wget|curl|45\.156\.24\.168|rplant|mining|stratum" "$f" \
    | tee -a "${OUT}/grep_shell_persistence.txt" || true
done
echo

echo "[6] Capture PM2 artefacts (if any exist)"
ls -lah /root 2>/dev/null | tee "${OUT}/ls_root.txt" || true
find /root -maxdepth 3 -type f -name "*ecosystem*.js" -o -name "*process*.json" -o -name "*.pm2*" 2>/dev/null \
  | tee "${OUT}/pm2_ecosystem_candidates.txt" || true
echo

echo "[7] Immediate containment: block known miner IP + common stratum ports"
# Known IP from your logs:
run "iptables -C OUTPUT -d 45.156.24.168 -j DROP 2>/dev/null || iptables -A OUTPUT -d 45.156.24.168 -j DROP"
# Common mining ports
for port in 3333 4444 5555 7777 9000 14444; do
  run "iptables -C OUTPUT -p tcp --dport ${port} -j REJECT 2>/dev/null || iptables -A OUTPUT -p tcp --dport ${port} -j REJECT"
done
echo

echo "[8] Kill known suspicious processes (xmrig/node/pm2/watchers)"
# Try graceful first, then hard kill
run "pkill -f -15 xmrig || true"
run "pkill -f -15 watcher || true"
run "pkill -f -15 systemhelper || true"
run "pkill -f -15 syshelper || true"
run "pkill -f -15 pm2 || true"
run "pkill -f -15 'PM2 v' || true"
run "pkill -f -15 node || true"
sleep 2
run "pkill -f -9 xmrig || true"
run "pkill -f -9 watcher || true"
run "pkill -f -9 systemhelper || true"
run "pkill -f -9 syshelper || true"
run "pkill -f -9 pm2 || true"
run "pkill -f -9 'PM2 v' || true"
run "pkill -f -9 node || true"
echo

echo "[9] Disable and remove likely PM2 systemd services (pm2-root / pm2-* / custom)"
# Stop/disable any unit with pm2 in its name
PM2_UNITS="$(systemctl list-unit-files --no-pager | awk '{print $1}' | egrep -i '^pm2.*\.service$' || true)"
for u in $PM2_UNITS; do
  run "systemctl stop ${u} || true"
  run "systemctl disable ${u} || true"
  run "systemctl mask ${u} || true"
done

# Also hunt for nonstandard units calling pm2/node
# If grep found suspect unit files, try to disable those units too:
if [[ -s "${OUT}/grep_systemd_persistence.txt" ]]; then
  awk -F: '{print $1}' "${OUT}/grep_systemd_persistence.txt" | sort -u | tee "${OUT}/suspect_unit_file_paths.txt" >/dev/null
  while read -r path; do
    [[ -f "$path" ]] || continue
    base="$(basename "$path")"
    if [[ "$base" == *.service || "$base" == *.timer ]]; then
      run "systemctl stop ${base} 2>/dev/null || true"
      run "systemctl disable ${base} 2>/dev/null || true"
      run "systemctl mask ${base} 2>/dev/null || true"
    fi
  done < "${OUT}/suspect_unit_file_paths.txt"
fi

run "systemctl daemon-reload"
echo

echo "[10] Neutralize cron-based persistence (only removes suspicious lines, backs up first)"
backup_dir="${OUT}/cron_backups"
run "mkdir -p ${backup_dir}"

# System-wide cron files
for f in /etc/crontab /etc/cron.d/*; do
  [[ -f "$f" ]] || continue
  run "cp -a \"$f\" \"${backup_dir}/$(basename "$f").bak\""
  # Remove only lines containing obvious persistence keywords
  run "sed -i -E '/pm2|xmrig|45\\.156\\.24\\.168|rplant|mining|stratum|kdevtmpfsi|kinsing|watcher|systemhelper|syshelper|curl |wget /Id' \"$f\""
done

# Root's crontab (if present)
if [[ -f /var/spool/cron/crontabs/root ]]; then
  run "cp -a /var/spool/cron/crontabs/root \"${backup_dir}/root_crontab.bak\""
  run "sed -i -E '/pm2|xmrig|45\\.156\\.24\\.168|rplant|mining|stratum|kdevtmpfsi|kinsing|watcher|systemhelper|syshelper|curl |wget /Id' /var/spool/cron/crontabs/root"
fi

# Older distros path
if [[ -f /var/spool/cron/root ]]; then
  run "cp -a /var/spool/cron/root \"${backup_dir}/root_crontab_legacy.bak\""
  run "sed -i -E '/pm2|xmrig|45\\.156\\.24\\.168|rplant|mining|stratum|kdevtmpfsi|kinsing|watcher|systemhelper|syshelper|curl |wget /Id' /var/spool/cron/root"
fi
echo

echo "[11] Remove PM2 root state dir (if recreated) and block resurrection"
# If PM2 daemon keeps respawning, masking pm2 services helps; still remove the dir.
run "rm -rf /root/.pm2 || true"
echo

echo "[12] Remove common miner artefacts (targeted, not wiping the system)"
# Known temp locations
run "find /tmp /var/tmp -maxdepth 2 -type f -iname '*xmrig*' -o -iname '*miner*' -o -iname '*watcher*' 2>/dev/null | tee ${OUT}/tmp_miner_files.txt || true"
run "find /tmp /var/tmp -maxdepth 2 -type f -iname '*xmrig*' -o -iname '*miner*' -o -iname '*watcher*' -delete 2>/dev/null || true"

# Common drop locations
run "find /usr/local/bin /usr/local/sbin /usr/bin /bin -maxdepth 1 -type f -iname '*xmrig*' -o -iname '*kdevtmpfsi*' -o -iname '*kinsing*' 2>/dev/null | tee ${OUT}/bin_miner_files.txt || true"
# Do NOT auto-delete binaries in /usr/bin or /bin (risky). Only report.
# If found in /usr/local/bin or /usr/local/sbin, it’s safer to remove:
run "find /usr/local/bin /usr/local/sbin -maxdepth 1 -type f \\( -iname '*xmrig*' -o -iname '*kdevtmpfsi*' -o -iname '*kinsing*' -o -iname '*watcher*' \\) -delete 2>/dev/null || true"

# Hidden dot dirs in /root and /etc
run "find /root /etc -maxdepth 3 -type f -o -type d 2>/dev/null | egrep -i '/\\.(system|xm|rig|b4nd1d0|est1|kinsing|kdevtmpfsi)' | tee ${OUT}/hidden_suspects.txt || true"
echo

echo "[13] Re-check: does PM2/node/xmrig still respawn?"
ps auxwwf | egrep -i "xmrig|minerd|miner|crypto|watcher|systemhelper|syshelper|pm2|node" \
  | tee "${OUT}/ps_post_cleanup.txt" || true
echo

echo "============================================================"
echo " FINDINGS TO PASTE BACK HERE (copy these files' key sections)"
echo " 1) ${OUT}/grep_systemd_persistence.txt"
echo " 2) ${OUT}/grep_cron_persistence.txt"
echo " 3) ${OUT}/ps_post_cleanup.txt"
echo " 4) ${OUT}/pm2_ecosystem_candidates.txt"
echo "============================================================"
echo
echo "Done. Output folder: ${OUT}"
BASH

chmod +x /root/one_shot_miner_cleanup.sh
