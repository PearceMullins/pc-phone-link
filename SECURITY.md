<!-- Security threat model and instructions for reporting vulnerabilities. -->
# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |

## Threat model

PC Phone Link is designed for **local network use** on a trusted home or office LAN (or VPN such as Tailscale). It is **not** intended to be exposed directly to the public internet.

### What the app protects

- **Connect code** — Shown on the PC terminal and phone so you can confirm you reached the correct PC before connecting
- **Paired browser tokens** — Required for control APIs and streaming after the first connect
- **Trusted device list** — Paired browsers are stored locally; you can revoke access

### What the app does not provide

- **No HTTPS/TLS** — Traffic between phone and PC is plain HTTP on your LAN
- **No encryption of streamed video** — Window capture is sent over the local network unencrypted
- **No account system** — Security relies on network isolation and paired browser tokens

Anyone on your LAN who can reach the host could read the connect code from `/api/connect-info` and attempt to connect. Treat your network as the primary security boundary.

## Reporting a vulnerability

If you discover a security issue, please **do not** open a public GitHub issue with exploit details.

Instead, open a **private security advisory** on GitHub:

1. Go to the repository **Security** tab
2. Click **Report a vulnerability**
3. Describe the issue, impact, and steps to reproduce

You can also contact the repository owner through GitHub if advisories are unavailable.

We aim to acknowledge reports within 7 days.

## Recommendations for users

- Keep the host bound to your LAN; do not port-forward to the internet without additional protection
- Revoke paired browsers you no longer use
- Prefer a VPN (Tailscale, WireGuard) when accessing your PC from outside the home network
- Enable Windows Firewall rules only for the ports you need (8765 host, 8780 wake relay)
