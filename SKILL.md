---
name: wordpress-selfhosted
license: MIT
description: "Create, edit, publish, or delete content on a self-hosted WordPress site over SSH+WP-CLI (or the REST API when the host is reachable directly over HTTPS): posts, pages, and the visible text on them. Use it to draft and publish posts (with SEO/Yoast meta, categories, tags, featured images, author assignment), edit existing copy (header, hero, footer, about page), fix a typo on a live page, find where a string lives across the database or theme and replace it, and purge caches after a change — down to a single one-line edit. For WordPress the user hosts themselves on LXC, VPS, or bare-metal, often behind Cloudflare or a reverse proxy (typically signaled by an SSH login plus a wp-root path). NOT for WordPress.com-hosted blogs, theme CSS/layout or plugin development, or server-to-server site migrations."
metadata: { "openclaw": { "emoji": "📝", "requires": { "bins": ["ssh", "scp", "curl", "jq"], "anyBins": ["op"], "env": ["WP_HOST", "WP_SSH_USER", "WP_ROOT"] }, "os": ["darwin", "linux"] } }
---

# WordPress Self-Hosted

Manage a self-hosted WordPress site via SSH+WP-CLI (primary) or WP REST API (when direct HTTPS access is available).

**Configuration — set via `openclaw.json` `skills.entries.wordpress-selfhosted.env` (preferred) or shell environment. Falls back to TOOLS.md if set there.**
- `WP_HOST` — LAN IP or domain, e.g., `myblog.com` **(required, gated)**
- `WP_SSH_USER` — SSH user, e.g., `dev` **(required, gated)**
- `WP_ROOT` — WordPress root path, e.g., `/var/www/html/wordpress` **(required, gated)**
- `WP_USER` — WordPress username (optional; set in TOOLS.md or env)
- `WP_1P_ITEM` — 1Password item name for app password (optional; set in TOOLS.md or env)

**Helper scripts** (in `scripts/`, run over SSH, read the env vars above):
`create-post.sh`, `set-post-meta.sh`, `set-featured-image.sh`, `locate-string.sh`, `purge-verify.sh`.
Prefer these for their deterministic step — the body keeps only the judgment.

**Remote host requirement:** WP-CLI (`wp`) must be installed on the WordPress host at `WP_HOST`, not on the local machine. Local requirements are only the connection and parsing tools used to reach that host: `ssh`, `scp`, `curl`, and `jq`.

## Connection Decision Tree

**Use SSH+WP-CLI when:**
- WordPress is on a LAN IP (HTTP only)
- Site is behind Cloudflare or a reverse proxy that strips Authorization headers
- `SITEURL` is `https://` but you're connecting over HTTP (SSL mismatch blocks app passwords)
- You need plugin/theme/DB/cache operations (REST can't do these anyway)

**Use REST API when:** you have direct HTTPS access (no proxy stripping headers) and `SITEURL` matches the URL you're calling. Verify with `curl -s "https://<wp-host>/wp-json/" | jq '.authentication'` (must be non-empty). Commands + app-password setup: **`references/rest-api.md`**. Common blockers: Cloudflare/proxies strip `Authorization`; WordPress requires SSL for app passwords (HTTP LAN fails); Wordfence can disable app passwords entirely.

## SSH + WP-CLI (Primary)

Use for all content operations, and the only option for plugin/theme/DB/cache work.

```bash
# macOS with 1Password SSH agent (drop -o StrictHostKeyChecking=accept-new once the host key is in known_hosts)
SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" \
  ssh -o StrictHostKeyChecking=accept-new <ssh-user>@<wp-host> 'cd <wp-root> && wp <command>'

# Linux / other SSH agents — SSH_AUTH_SOCK is already set in most environments
ssh -o StrictHostKeyChecking=accept-new <ssh-user>@<wp-host> 'cd <wp-root> && wp <command>'
```

⚠️ **macOS + 1Password:** use `pty: true` on exec calls — the agent needs a PTY for Touch ID signing, else `communication with agent failed`.

### File upload & temp handling

Write large content bodies to a local temp file and SCP them over (avoids shell-quoting issues with HTML). Use a restrictive umask and clean up after:

```bash
umask 077 && cat > /tmp/post-content.html << 'CONTENT'
...Gutenberg HTML...
CONTENT
SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" \
  scp -o StrictHostKeyChecking=accept-new /tmp/post-content.html <ssh-user>@<wp-host>:/tmp/
# after use:
rm -f /tmp/post-content.html && ssh <ssh-user>@<wp-host> 'rm -f /tmp/post-content.html'
```

Temp files hold post HTML only — never credentials. (The `create-post.sh` / `set-featured-image.sh` helpers do this upload + cleanup for you.)

## Create & Publish a Post

1. **Gather context** — list existing posts to link 2–3 internally:
   ```bash
   ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post list --post_status=publish --fields=ID,post_title,post_name --format=json'
   ```
2. **Write the body** to a local `.html` file in clean Gutenberg block format — see **`references/post-format.md`** (pure editorial content; author signatures and persona attribution are handled automatically at the theme template layer via `--author`).
   - **Mandatory Sanitization SOP (Full Surface Audit):** Enforce RFC-compliant placeholders across all layers:
     - Domains: RFC 2606/6761 `example.com`, `client.example.com` (never real client, internal, or production domains).
     - Network: RFC 5737 public IPs (`203.0.113.0/24`), RFC 1918 generic documentation subnets (`10.0.10.0/24`, `172.16.10.0/24`, `192.168.1.100`). Never leak real private infrastructure subnets or router IPs.
     - Physical Locations: Never leak physical street names, geographic landmarks, or personal room labels -> use `primary site`, `workstation VM`.
     - Hardware Specs: Never leak retail CPU/GPU hardware models, enterprise chassis tags, or personal drive brands -> use `8-core desktop processor`, `workstation GPU`, `1U enterprise rack server`.
     - Hostnames & Daemons: Never leak cluster hypervisor nodes or tunnel daemon identifiers -> use `primary-hypervisor`, `pbs-storage`, `homelab-ingress`.
     - Tokens & UUIDs: Explicit bracketed placeholders (`<YOUR-TUNNEL-UUID>`, `<YOUR-TUNNEL-TOKEN>`).
     - Full SOP: **`references/post-format.md#rfc-compliant-placeholders--sanitization-sop`**.
3. **Create** (returns the new ID):
   ```bash
   scripts/create-post.sh --file /tmp/post-content.html --title "Post Title" --status draft --author <user-id>
   ```
   *(Note: `create-post.sh` automatically runs `validate-gutenberg.py` and `validate-sanitization.py` on the content and title before submission).*
4. **Set taxonomy + SEO**:
   ```bash
   scripts/set-post-meta.sh <ID> --category <slug> --tags "tag1 tag2" \
     --metadesc "120–155 char description" --focuskw "focus keyphrase"
   ```
   *(Note: `set-post-meta.sh` automatically runs `validate-sanitization.py` on metadesc and focuskw).*
5. **Featured image** (optional): `scripts/set-featured-image.sh <ID> /path/to/image.png "Title"`
6. **Pre-flight verification before publishing**:
   - **RFC Placeholders & Security Sanitization**: Run `python3 scripts/validate-sanitization.py <file.html>` to verify zero leaks. Audit `wp_postmeta` (`_yoast_wpseo_metadesc`, `_tldr_takeaways`) and media alt text (`_wp_attachment_image_alt`).
   - **SEO Check**: meta description (120–155 chars), focus keyphrase, 2–3 internal links, 5–7 tags, category, featured image. Score 90+ via `analyze_seo.py`.
7. **Publish**: `ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post update <ID> --post_status=publish'`

## Editing Existing Content

The flow above *creates* posts. Editing existing content needs two things it doesn't: finding where the text actually lives, and changing it in place without rebuilding the post by hand.

**Find where a string lives** — run `scripts/locate-string.sh "<distinctive fragment>"`. It checks, in the order strings most commonly live, `post_content` → `wp_options` → `wp_postmeta` → active-theme files (deps excluded) and reports the hits. Check the DB *before* theme files: block/hybrid themes (Sage, FSE) routinely render raw HTML stored in a page, so text that looks template-driven usually isn't. Search a short, distinctive middle fragment, not a whole line — separators (`|`, `·`), entities (`&amp;`), and smart quotes differ between rendered and stored text. (A string found only in a compiled `public/`/`dist/` bundle is built at build time — fix the theme source and rebuild, not the bundle.)

**Edit post content in place** — pull, edit locally, push back; never reconstruct the body:

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post get <ID> --field=post_content' > /tmp/post-<ID>.html
# edit /tmp/post-<ID>.html (only the target strings — keep it as your rollback copy), then:
scp /tmp/post-<ID>.html <ssh-user>@<wp-host>:/tmp/ && \
  ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post update <ID> /tmp/post-<ID>.html'
```

Editing locally avoids host-side `sed` quoting/locale pitfalls with HTML, pipes, and multibyte glyphs (`·`, em dashes). For an options/postmeta value, update it directly (`wp option update` / `wp post meta update`). Prefer this round-trip over `wp search-replace` for a single known edit — search-replace rewrites every revision and gives no diff (always `--dry-run` first if you use it).

## Cache Invalidation & Verifying Changes

A WP-CLI write is persisted the moment `wp post update` returns, but caches can still serve the old version. After any edit, run `scripts/purge-verify.sh <public-url> "<new string>"`: it flushes the object cache + transients, flags active cache/CDN plugins, then fetches the public URL from outside the LAN and confirms the new string is live (reading `cf-cache-status`). The official `cloudflare` plugin auto-purges the edge on update, so a `HIT` is fine **as long as the fetched HTML already shows the new content**. Always verify externally — an internal/DB check can pass while the edge is stale.

> Full manual runbook for editing/locating/cache (raw queries, edge cases, plugin-specific flush commands): **`references/editing-existing-content.md`** — read it only when the scripts can't be used.

## Authors

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp user list --fields=ID,user_login,display_name --format=json'
```

Common pattern for AI-assisted blogs: separate author accounts for human vs. agent-authored posts.

## Security Notes

**`StrictHostKeyChecking=accept-new`** (the default here) trusts a host on first connect and rejects changed keys after — MITM protection post-connect, suitable for user-configured hosts on trusted LANs. **Best:** pre-populate the key once (`ssh-keyscan -H <wp-host> >> ~/.ssh/known_hosts`) and drop the flag. **CI/ephemeral only:** `-o StrictHostKeyChecking=no` disables verification — not for interactive/persistent use.

**1Password SSH agent (macOS):** commands reference `SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"` to sign via Touch ID without private keys on disk (needs `pty: true`). On Linux, the standard `SSH_AUTH_SOCK` is used.

**Capabilities & footprint** (declared for transparency):
- **Network:** SSH/SCP to the user-configured `WP_HOST` only; `curl` to the public URL passed to `purge-verify.sh` (and, on the REST path, HTTPS to that host's `/wp-json`). No other endpoints, no telemetry.
- **Credentials:** SSH key via ssh-agent (never written to disk). On the REST path, a WP application password is read at runtime via `op item get --reveal` into a shell variable (`op://` references aren't supported by curl) — not cached to disk. Config values `WP_HOST`/`WP_SSH_USER`/`WP_ROOT` are gated env vars (`requires.env`); `WP_USER`/`WP_1P_ITEM` optional.
- **File writes:** temporary `/tmp/*.html` content files (mode 600 via `umask 077`), SCP'd to the host and cleaned up after use. Helper scripts remove their remote temp files automatically.
