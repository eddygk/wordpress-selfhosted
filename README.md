# wordpress-selfhosted

An OpenClaw skill for managing self-hosted WordPress sites via WP REST API and SSH+WP-CLI.

## What It Does

- **Create, draft, publish, update, and delete** posts and pages via WP REST API
- **SEO optimization** — meta descriptions, focus keywords, slugs, Yoast/Rank Math support
- **Author assignment** — separate human and AI agent author profiles
- **Categories, tags, and featured images**
- **SSH+WP-CLI fallback** for low-level ops (plugin installs, cache flush, DB work)
- **1Password integration** for credential hydration

## Requirements

- `curl`, `jq` — for REST API calls
- `ssh`, `scp`, `wp-cli` — for SSH+WP-CLI fallback
- `op` (optional) — 1Password CLI for credential hydration
- A self-hosted WordPress install (LXC, VPS, bare-metal)
- A WordPress application password for API auth

## Quick Setup

1. Create a WP application password via SSH:
   ```bash
   wp user application-password create <username> "MyAgent-OpenClaw" --porcelain
   ```
2. Store the output in 1Password (or your preferred secret manager)
3. Update `TOOLS.md` with your `WP_HOST`, `WP_USER`, `WP_SSH_USER`, `WP_ROOT`, and `WP_1P_ITEM`

## Usage

Once configured, ask your OpenClaw agent things like:

- *"Write a blog post about X and publish it as a draft"*
- *"Update the resume page with this new content"*
- *"List all published posts"*
- *"Set the featured image on post 42"*

## Design

Prefers **WP REST API** over SSH for all standard CRUD — no PTY, no Touch ID prompts, works over LAN or public domain. SSH+WP-CLI is reserved for operations the REST API can't handle.

## License

MIT
