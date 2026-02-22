# Deployment Matrix

## Deployment Modes

| Mode   | Worker Location      | When to Use                                                |
|--------|----------------------|-------------------------------------------------------------|
| **SaaS**   | Resolvify cloud      | Targets reachable from cloud (public IP, VPN, bastion)     |
| **PaaS**   | Customer jump server | Targets on private LAN only                                |
| **Hybrid** | Customer jump server | Backend in cloud; worker on-prem; worker pulls assignments |

## Network Requirements

### Worker

- **Outbound HTTPS** to `BACKEND_BASE_URL` (API calls: register, heartbeat, event publish)
- **Outbound TCP** to Redis host:port from `REDIS_URL`
- **Outbound SSH (22)** to target hosts or bastion/jump server

### On-Prem Worker

For on-prem workers (PaaS/Hybrid), use `network_mode: host` in Docker so the worker shares the host network and can reach LAN targets. If Redis/backend are on a different host, use port mappings instead of host network.

## Jump Server Placement and HA

- Run the worker on a jump server for PaaS deployments.
- If the jump host goes down, runbooks stop. Use existing jump recovery (console access, backup jump host).
- Optional: secondary jump + worker; backend could route to either (future enhancement).

## Bastion/ProxyJump

For targets reachable only via a bastion host, configure the Infrastructure Connection `meta_data` (JSON) with:

```json
{
  "bastion_host": "jump.example.com",
  "bastion_port": 22,
  "bastion_username": "jump_user",
  "bastion_password": "...",
  "bastion_private_key": "-----BEGIN OPENSSH PRIVATE KEY-----..."
}
```

Or reference bastion credentials via `bastion_credentials`:

```json
{
  "bastion_host": "jump.example.com",
  "bastion_credentials": {
    "username": "jump_user",
    "password": "...",
    "private_key": "..."
  }
}
```
