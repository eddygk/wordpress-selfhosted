---
name: wordpress-selfhosted
license: MIT
description: "Manage a self-hosted WordPress site via SSH+WP-CLI (primary) and WP REST API (when direct HTTPS access is available). Use when asked to write, draft, publish, update, or delete posts/pages on a self-hosted WordPress installation — including SEO optimization, categories/tags, featured images, author assignment, and proper post formatting. Designed for WordPress running on LXC, VPS, or bare-metal (not WordPress.com hosted). Requires: ssh, scp, curl, jq, wp (WP-CLI). Optional: op (1Password CLI for credential hydration). Network: user-configured WordPress host (LAN IP or public domain). Credentials: WP application password stored in 1Password (item: configurable)."
metadata:
  openclaw:
    requires:
      bins:
        - ssh
        - scp
        - curl
        - jq
        - wp
    os:
      - darwin
      - linux
---

# WordPress Self-Hosted

Manage a self-hosted WordPress site via SSH+WP-CLI (primary) or WP REST API (when direct HTTPS access is available).

**Configuration — set these from TOOLS.md before using:**
- `WP_HOST` — LAN IP or domain (e.g., `10.0.0.10` or `myblog.com`)
- `WP_USER` — WordPress username
- `WP_1P_ITEM` — 1Password item name for app password
- `WP_SSH_USER` — SSH user (e.g., `dev`)
- `WP_ROOT` — WordPress root path (e.g., `/var/www/html/wordpress`)

## Connection Decision Tree

**Use SSH+WP-CLI when:**
- WordPress is on a LAN IP (HTTP only)
- Site is behind Cloudflare or a reverse proxy that strips Authorization headers
- `SITEURL` is `https://` but you're connecting over HTTP (SSL mismatch blocks app passwords)
- You need plugin/theme/DB/cache operations (REST can't do these anyway)

**Use REST API when:**
- You have direct HTTPS access to the WordPress host (no proxy stripping headers)
- `SITEURL` matches the URL you're calling (no SSL mismatch)
- Verify first: `curl -s "https://<wp-host>/wp-json/" | jq '.authentication'` — must return non-empty

⚠️ **Common blockers for REST API auth:**
- Cloudflare (and most reverse proxies) strip `Authorization` headers — REST API auth will fail via public domain
- WordPress requires SSL for application passwords — HTTP LAN access fails even if app passwords are created
- Wordfence can disable application passwords entirely (`wf_prevent_application_passwords` option)

## SSH + WP-CLI (Primary)

Use for all content operations when REST API is unavailable. Also the only option for plugin installs, cache flush, DB operations, file management.

```bash
# macOS with 1Password SSH agent
SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" \
  ssh -o StrictHostKeyChecking=no <ssh-user>@<wp-host> \
  'cd <wp-root> && wp <command>'

# Linux / other SSH agents — SSH_AUTH_SOCK is already set in most environments
ssh -o StrictHostKeyChecking=no <ssh-user>@<wp-host> \
  'cd <wp-root> && wp <command>'
```

⚠️ **macOS + 1Password users:** Always use `pty: true` on exec tool calls — the 1Password agent needs a PTY for Touch ID signing. Without it: `communication with agent failed`.

### SCP (file upload)

Large content bodies should be written to a local temp file, SCP'd over, then passed via `$(cat /tmp/file)` — avoids shell quoting issues with HTML/special chars.

```bash
SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" \
  scp -o StrictHostKeyChecking=no /tmp/file.html <ssh-user>@<wp-host>:/tmp/
```

## WP REST API (When Direct HTTPS Available)

No PTY, no Touch ID, single HTTP call. Use only when connection decision tree above confirms it will work.

```bash
WP_USER="<wp-username>"
WP_PASS=$(op item get "<1p-item-name>" --fields password --reveal)
WP_BASE="https://<wp-host>/wp-json/wp/v2"

# Verify auth works before proceeding
curl -s -u "$WP_USER:$WP_PASS" "$WP_BASE/users/me" | jq '{id, name}'

# List posts
curl -s -u "$WP_USER:$WP_PASS" "$WP_BASE/posts?per_page=20&status=any" | jq '[.[] | {id, title: .title.rendered, status}]'

# Get post content (raw blocks)
curl -s -u "$WP_USER:$WP_PASS" "$WP_BASE/posts/<ID>?context=edit" | jq -r '.content.raw'

# Create post (draft)
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts" \
  -H "Content-Type: application/json" \
  -d '{"title":"Post Title","content":"<p>Body</p>","status":"draft"}'

# Update post content
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts/<ID>" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(cat /tmp/content.html | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}"

# Publish
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts/<ID>" \
  -H "Content-Type: application/json" \
  -d '{"status": "publish"}'
```

**To create an app password:**
```bash
wp user application-password create <username> "MyAgent" --porcelain
```
Store output in 1Password. Note: passwords are hashed in the DB — you can't recover them later.

## Quick Start Workflow (WP-CLI)

### 0. Pre-Write (gather context)

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post list --post_status=publish --fields=ID,post_title,post_name --format=json 2>/dev/null' | jq '[.[] | {id: .ID, title: .post_title, slug: .post_name}]'
```

Pick 2–3 related posts to link contextually in the content body.

### 1. Write content to temp file locally

Write Gutenberg HTML to `/tmp/post-content.html`, then SCP to host.

### 2. Create Draft

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && \
  wp post create /tmp/post-content.html \
  --post_title="Post Title" \
  --post_status=draft \
  --post_author=<user-id> \
  --porcelain 2>/dev/null'
# Returns post ID
```

### 3. Set Metadata

```bash
POST_ID=123
ssh <ssh-user>@<wp-host> 'cd <wp-root> && \
  wp post term set '"$POST_ID"' category <slug> && \
  wp post term set '"$POST_ID"' post_tag <tag1> <tag2> && \
  wp post meta update '"$POST_ID"' _yoast_wpseo_metadesc "Meta description 120-155 chars" && \
  wp post meta update '"$POST_ID"' _yoast_wpseo_focuskw "focus keyphrase" 2>/dev/null'
```

### 4. SEO Checklist

Before publishing, verify:
- [ ] Meta description set (120–155 chars)
- [ ] Focus keyphrase set
- [ ] 2–3 internal links to related posts
- [ ] 5–7 tags
- [ ] Categories assigned
- [ ] Featured image set (optional but recommended)

### 5. Publish

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post update '"$POST_ID"' --post_status=publish 2>/dev/null'
```

## Authors

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp user list --fields=ID,user_login,display_name --format=json 2>/dev/null'
```

Common pattern for AI-assisted blogs: separate author accounts for human posts vs. agent-authored posts.

## Post Content Format

Use WordPress block format (Gutenberg):

```html
<!-- wp:paragraph -->
<p>Paragraph text here.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2>Section Heading</h2>
<!-- /wp:heading -->

<!-- wp:code -->
<pre class="wp-block-code"><code>code here</code></pre>
<!-- /wp:code -->

<!-- wp:list -->
<ul>
<li>List item</li>
</ul>
<!-- /wp:list -->
```

## Author Signatures (optional)

Append at end of AI-authored posts:

```html
<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"},"color":{"text":"#888888"}}} -->
<p style="font-size:14px;color:#888888"><em>Written by <strong>Your Agent Name</strong> — AI agent (OpenClaw / Claude)<br>First-person perspective from an AI execution engine</em></p>
<!-- /wp:paragraph -->
```

## Featured Images

```bash
# SCP image to host first, then import
ssh <ssh-user>@<wp-host> 'cd <wp-root> && \
  ATTACH_ID=$(wp media import /tmp/image.png --title="Image Title" --porcelain 2>/dev/null) && \
  wp post meta update POST_ID _thumbnail_id $ATTACH_ID 2>/dev/null'
```
