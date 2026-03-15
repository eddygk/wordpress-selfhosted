# wordpress-selfhosted

An agent skill for managing self-hosted WordPress sites via SSH+WP-CLI and WP REST API.

## What It Does

- **Create, draft, publish, update, and delete** posts and pages
- **SEO optimization** — meta descriptions, focus keywords, slugs, Yoast/Rank Math support
- **Author assignment** — separate human and AI agent author profiles
- **Categories, tags, and featured images**
- **1Password integration** for credential hydration

## Requirements

- `ssh`, `scp`, `wp-cli` — primary method
- `curl`, `jq` — for REST API (when available)
- `op` (optional) — 1Password CLI for credential hydration
- A self-hosted WordPress install (LXC, VPS, bare-metal)

## Quick Setup

1. Update `TOOLS.md` with your `WP_HOST`, `WP_USER`, `WP_SSH_USER`, `WP_ROOT`, and `WP_1P_ITEM`
2. Confirm SSH access works: `ssh <WP_SSH_USER>@<WP_HOST> 'wp --info'`

## Usage

Once configured, ask your agent things like:

- *"Write a blog post about X and publish it as a draft"*
- *"Update the resume page with this new content"*
- *"List all published posts"*
- *"Set the featured image on post 42"*

## Design

**SSH+WP-CLI is primary.** WP REST API is supported but conditional — it requires direct HTTPS access with no proxy stripping Authorization headers. Common self-hosted setups (behind Cloudflare, LAN-only HTTP, Wordfence) break REST API auth. The skill includes a decision tree to determine which method to use.

## Compatibility

Works with any agent that can read markdown — OpenClaw, Claude Code, Codex, Cursor, or any tool that accepts instruction files. The `SKILL.md` frontmatter is OpenClaw/ClawHub packaging; the runbook content is agent-agnostic.

## License

MIT
