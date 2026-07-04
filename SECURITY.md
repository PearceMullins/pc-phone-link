<!-- Security threat model and instructions for reporting vulnerabilities. -->
# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |

## Threat model

PC Phone Link is designed for **local network use** on a trusted home or office LAN (or VPN such as Tailscale). It is **not** intended to be exposed directly to the public internet.

### What the app protects

- **Access token** — Required on every API call and in the control URL query string
- **Dual-approval pairing** — New browsers must be approved on both the PC and the phone
- **Trusted device list** — Paired browsers are stored locally; you can revoke access

### What the app does not provide

- **No HTTPS/TLS** — Traffic between phone and PC is plain HTTP on your LAN
- **No encryption of streamed video** — Window capture is sent over the local network unencrypted
- **No account system** — Security relies on network isolation and the access token

Treat your access token like a password. Anyone on your network who knows the token and pairing is approved can control your PC.

## Reporting a vulnerability

If you discover a security issue, please **do not** open a public GitHub issue with exploit details.

Instead, open a **private security advisory** on GitHub:

1. Go to the repository **Security** tab
2. Click **Report a vulnerability**
3. Describe the issue, impact, and steps to reproduce

You can also contact the repository owner through GitHub if advisories are unavailable.

We aim to acknowledge reports within 7 days.

## Recommendations for users

- Keep the host and launcher bound to your LAN; do not port-forward to the internet without additional protection
- Use a strong, unique access token (the app generates one by default)
- Revoke paired browsers you no longer use
- Prefer a VPN (Tailscale, WireGuard) when accessing your PC from outside the home network
- Enable Windows Firewall rules only for the ports you need (8764 launcher, 8765 host, 8780 wake relay)
