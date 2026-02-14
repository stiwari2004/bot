# Jump Server Discovery – Goal and Next Steps

## Goal (what the user wants)

- Install the discovery agent **once on the jump server**.
- Run **one command** (e.g. `python3 discover.py "INGEST_URL" "TOKEN"`).
- The agent **scans every host** the jump server can reach (everything “connected” to it) and reports them to the frontend.

No manual server list, no editing config per host – it should discover and report everything from the jump server.

## What’s going wrong today

1. **Auto-discovery sources are weak on this setup**
   - `/etc/hosts` often only has the jump server itself and a few names.
   - `~/.ssh/known_hosts` is **hashed** (`HashKnownHosts yes`), so entries look like `|1|base64|base64|` and cannot be used as connection targets. We correctly skip those, but then we get no hosts from known_hosts.
   - So after filtering (skip self, skip hashed), we often end up with **zero** hosts to scan, and discovery “does nothing”.

2. **Result**
   - Either “Reported 1/1” (only the jump host) or “0/8” and then 1/1 after we started filtering – so the “install on jump and scan everything” use case is not working.

## What actually works today

- Running `discover.py` with URL + token (after CRLF fix).
- Ingest and run_id reuse: multiple assets go into one run and show in the UI.
- Manual `config.yaml` with `remote_servers.servers` filled by hand: if you list hosts explicitly, SSH discovery and reporting work.

So the **reporting path** is fine; the **discovery of “everything from the jump”** is what’s missing.

## Direction for tomorrow (so we don’t keep patching in the dark)

**Option A – Simple server list file (quick win)**  
- If a file exists, e.g. `servers.txt` in the discovery-agent folder, read it: one hostname or IP per line.  
- User can populate it once, e.g. from `~/.ssh/config` or their inventory.  
- No dependency on hashed known_hosts or /etc/hosts.  
- Gives a clear “list of what to scan” that we control.

**Option B – Subnet / range scan (real “discover everything”)**  
- Add config (or a simple default), e.g. `scan_subnets: ["192.168.48.0/24"]` or a single “scan range” for the jump server’s network.  
- From the jump server: ping or TCP connect to port 22 on that range, then for each responding host try SSH (with the same key/user as the jump).  
- No reliance on known_hosts or /etc/hosts; works even when everything is hashed.  
- Requires deciding how to get the subnet (config, or auto-detect from jump server’s IP).

**Option C – Use `~/.ssh/config`**  
- Parse `~/.ssh/config` and collect `Host` entries that are not wildcards; use those as the list of hosts to try.  
- Gives “everything I normally SSH to from this jump” without maintaining a separate list.  
- Needs to skip the jump server itself and handle edge cases (wildcards, proxies).

**Recommendation**  
- **Tomorrow:** implement **Option A** (servers.txt) so there’s one simple, reliable way to “scan everything I care about” from the jump server, and document it (e.g. “To scan all servers from the jump, list them in `servers.txt`, one per line”).  
- Then, if the user wants zero-config discovery, add **Option B** (subnet scan) and/or **Option C** (ssh config) so “install on jump and run one command” really does scan everything connected, without depending on unhashed known_hosts.

## Files to touch tomorrow

- `run_discovery.py` – where we build `servers_to_scan`: add reading from `servers.txt` (and optionally subnet or ssh config).
- `REMOTE_SERVERS_SETUP.md` or README – document “for jump server: put hosts in servers.txt or set scan_subnets”.
- Optionally a small script or doc line: “how to populate servers.txt from ssh config or inventory”.

No code changes in this file; this is a handover note so we continue in one direction tomorrow.
