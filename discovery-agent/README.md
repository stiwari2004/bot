# Resolvify Discovery Scanner

**One command** discovers this host, network devices (routers, switches), and storage (SAN/NAS), and sends everything to Resolvify. Works on **Windows**, **Linux**, and **macOS**. No config file. No separate install.

---

## One step

1. In Resolvify go to **Tenant Admin → Discovery**.
2. Click **Generate token** and copy the token (shown once).
3. Copy the **one command** shown on that page (Linux/macOS or Windows), replace `YOUR_TOKEN` with the token you copied, and run it in a terminal on the machine you want to scan.

That command fetches the scanner, installs dependencies, and runs full discovery (this host + network + storage). Nothing to install or configure by hand.

**Requirements:** Python 3.6+ and network access to your Resolvify app. The command uses your app’s ingest URL; you only paste your token.

---

## What gets discovered

- **This host** (Windows, Linux, or macOS)
- **Network devices** (routers, switches) if you later add a `config.yaml` with `network.devices` and run from the discovery-agent folder
- **Storage / SAN / NAS** if you add `storage.targets` in config

By default the one command reports this host. For network and storage you can copy the discovery-agent folder, add a `config.yaml` with devices/targets, and run `python run.py` (or `python3 run.py`) from that folder.

---

## Optional: config for network and storage

If you have the discovery-agent folder (e.g. from the repo), you can add a `config.yaml` (from `config.sample.yaml`) and set `network.enabled: true` with a list of `devices`, and/or `storage.enabled: true` with `targets`. Then run `python run.py` (or `run.bat` / `./run.sh`) from that folder so the same run includes network and storage.

---

## Security

- Keep the token secret; do not commit or log it.
- Use HTTPS for your Resolvify URL in production.
