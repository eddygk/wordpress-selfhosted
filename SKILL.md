---
name: wordpress-selfhosted
description: "Manage a self-hosted WordPress site via WP REST API (preferred) and SSH+WP-CLI (fallback for low-level ops). Use when asked to write, draft, publish, update, or delete posts/pages on a self-hosted WordPress installation — including SEO optimization, categories/tags, featured images, author assignment, and proper post formatting. Designed for WordPress running on LXC, VPS, or bare-metal (not WordPress.com hosted). Requires: ssh, scp, curl, jq, wp-cli. Optional: op (1Password CLI for credential hydration). Network: user-configured WordPress host (LAN IP or public domain). Credentials: WP application password stored in 1Password (item: configurable)."
metadata: { "openclaw": { "requires": { "bins": ["ssh", "scp", "curl", "jq", "wp-cli"] }, "os": ["darwin", "linux"] } }
---

# WordPress Self-Hosted

Manage a self-hosted WordPress site via WP REST API (preferred) or SSH+WP-CLI (fallback).

**Configuration — set these from TOOLS.md before using:**
- `WP_HOST` — LAN IP or domain (e.g., `10.0.0.10` or `myblog.com`)
- `WP_USER` — WordPress username
- `WP_1P_ITEM` — 1Password item name for app password
- `WP_SSH_USER` — SSH user (e.g., `dev`)
- `WP_ROOT` — WordPress root path (e.g., `/var/www/html/wordpress`)

## Connection

### WP REST API (preferred for post/page CRUD)

No PTY, no Touch ID, single HTTP call. Use for all standard content operations.

```bash
WP_USER="<wp-username>"
WP_PASS=$(op item get "<1p-item-name>" --fields password --reveal)
WP_BASE="http://<wp-host>/wp-json/wp/v2"

# List pages
curl -s -u "$WP_USER:$WP_PASS" "$WP_BASE/pages?per_page=20" | jq '[.[] | {id, title: .title.rendered, status}]'

# Get page content
curl -s -u "$WP_USER:$WP_PASS" "$WP_BASE/pages/<ID>" | jq '.content.raw'

# Update page
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/pages/<ID>" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(cat /tmp/content.html | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}"

# Create post (draft)
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts" \
  -H "Content-Type: application/json" \
  -d '{"title":"Post Title","content":"<p>Body</p>","status":"draft"}'
```

**To create an app password:** SSH in and run:
```bash
wp user application-password create <username> "MyAgent-OpenClaw" --porcelain
```
Store the output in 1Password (or your preferred secret manager).

### SSH + WP-CLI (fallback — low-level ops only)

Use for: plugin installs, cache flush, DB operations, file management.

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

```bash
# macOS with 1Password SSH agent
SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" \
  scp -o StrictHostKeyChecking=no /tmp/file.html <ssh-user>@<wp-host>:/tmp/
```

## Quick Start Workflow

### 0. Pre-Write (gather context)

```bash
# List existing posts for internal linking
curl -s "$WP_BASE/posts?per_page=50&status=publish" | jq '[.[] | {id, title: .title.rendered, slug}]'
```

Pick 2–3 related posts to link contextually in the content body.

### 1. Create Draft

```bash
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Post Title\",
    \"content\": $(cat /tmp/post-content.html | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    \"status\": \"draft\",
    \"author\": AUTHOR_ID
  }"
```

### 2. Set Metadata

```bash
# Get post ID from step 1, then set categories, tags, excerpt, SEO meta
POST_ID=123

# Categories and tags (use term IDs or slugs via REST)
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d '{"categories": [1, 2], "tags": [3, 4, 5], "excerpt": "Brief description..."}'

# SEO meta (Yoast / Rank Math — via WP-CLI if REST doesn't expose it)
ssh <ssh-user>@<wp-host> 'cd <wp-root> && \
  wp post meta update '"$POST_ID"' _yoast_wpseo_metadesc "Meta description 120-155 chars" && \
  wp post meta update '"$POST_ID"' _yoast_wpseo_focuskw "focus keyphrase"'
```

### 3. SEO Checklist

Before publishing, verify:
- [ ] Meta description set (120–155 chars)
- [ ] Focus keyphrase set
- [ ] 2–3 internal links to related posts
- [ ] 5–7 tags
- [ ] Categories assigned
- [ ] Featured image set (optional but recommended)

### 4. Publish

```bash
curl -s -X POST -u "$WP_USER:$WP_PASS" "$WP_BASE/posts/$POST_ID" \
  -H "Content-Type: application/json" \
  -d '{"status": "publish"}'
```

## Authors

WordPress supports multiple author profiles. List yours:

```bash
curl -s "$WP_BASE/users" | jq '[.[] | {id, name, slug}]'
```

Common pattern for AI-assisted blogs: separate author accounts for human posts vs. agent-authored posts. Set `author` (user ID) when creating posts.

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
# Import local image as WP media attachment
ssh <ssh-user>@<wp-host> 'cd <wp-root> && \
  wp media import /tmp/image.png --title="Image Title" --porcelain'

# Set as featured image (use attachment ID returned above)
ssh <ssh-user>@<wp-host> 'cd <wp-root> && \
  wp post meta update POST_ID _thumbnail_id ATTACHMENT_ID'
```
