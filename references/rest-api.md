# WP REST API path

Read this only when the Connection Decision Tree (in SKILL.md) confirms REST will work: direct HTTPS to the host, `SITEURL` matches, no proxy stripping `Authorization`. Most self-hosted setups (behind Cloudflare, LAN-only HTTP, Wordfence) break REST auth — use SSH+WP-CLI instead.

No PTY, no Touch ID, single HTTP call.

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
