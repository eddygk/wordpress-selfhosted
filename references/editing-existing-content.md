# Editing Existing Content — manual runbook

Read this when the helper scripts (`scripts/locate-string.sh`, `scripts/purge-verify.sh`) can't be used, or when you need the raw queries / edge cases. The SKILL.md body covers the judgment; this file is the detail.

## Find where a string lives (manual)

Check in this order — most common and cheapest first — and stop when you find it. The scripted version runs all four for you.

**1. Page/post content (`post_content`)** — most user-visible copy lives here, including large blocks of hand-written HTML. Block/hybrid themes (Sage, FSE) routinely render raw HTML stored in a page, so text that *looks* template-driven often isn't. Check the DB before grepping theme files.

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp db query \
  "SELECT ID, post_title, post_type, post_status FROM wp_posts \
   WHERE post_content LIKE '"'"'%SEARCH FRAGMENT%'"'"'"'
```

**2. Options (`wp_options`)** — site title, tagline, widget text, theme-mod settings, plugin config.

```bash
ssh ... 'cd <wp-root> && wp db query \
  "SELECT option_id, option_name FROM wp_options WHERE option_value LIKE '"'"'%SEARCH FRAGMENT%'"'"'"'
```

**3. Post meta (`wp_postmeta`)** — ACF fields, page-builder payloads, SEO fields (Yoast/Rank Math).

```bash
ssh ... 'cd <wp-root> && wp db query \
  "SELECT meta_id, post_id, meta_key FROM wp_postmeta WHERE meta_value LIKE '"'"'%SEARCH FRAGMENT%'"'"'"'
```

**4. Theme files** — only if the string isn't in the DB. Grep the *active* theme (`wp option get stylesheet` gives its dir), excluding deps:

```bash
ssh ... 'cd <wp-root>/wp-content/themes/<active-theme> && \
  grep -rni "SEARCH FRAGMENT" . --include="*.php" --include="*.blade.php" --include="*.js" \
  | grep -vE "node_modules|/vendor/"'
```

If the string appears only in a compiled bundle under `public/`/`dist/` (not in `resources/`), it's baked in at build time — edit the source and rebuild (`npm run build` / `yarn build` in the theme dir), never the compiled file.

**Pick a distinctive fragment, not the whole line.** Separators (`|`, `·`), HTML entities (`&amp;`), and smart quotes frequently differ between what renders and what's stored, so a `LIKE` on a short literal middle chunk matches reliably where pasting the entire string fails.

## Edit post content in place (round-trip)

Don't reconstruct a post body from scratch. Pull, edit locally, push back — this changes only what you touched and leaves a clean revision behind:

```bash
# 1. Pull current content to a local file — also your rollback copy
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post get <ID> --field=post_content' > /tmp/post-<ID>.html

# 2. Edit /tmp/post-<ID>.html locally, changing only the target strings

# 3. Push it back, then confirm the new content landed
SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock" \
  scp -o StrictHostKeyChecking=accept-new /tmp/post-<ID>.html <ssh-user>@<wp-host>:/tmp/
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp post update <ID> /tmp/post-<ID>.html'
```

Editing locally instead of running `sed` on the host sidesteps shell-quoting and locale pitfalls with HTML, pipe characters, and multibyte glyphs (`·`, em dashes, smart quotes). Keep the original `/tmp/post-<ID>.html` until you've verified the live site — re-running `wp post update <ID>` against the unedited copy rolls it back.

For a value in `wp_options` or `wp_postmeta`, update it directly rather than round-tripping:

```bash
ssh ... 'cd <wp-root> && wp option update <option_name> "<new value>"'
ssh ... 'cd <wp-root> && wp post meta update <post_id> <meta_key> "<new value>"'
```

`wp search-replace 'old' 'new' wp_posts --dry-run` is the right tool for a true site-wide string swap, but it also rewrites every revision and gives you no diff to inspect — for a single known edit, prefer the round-trip. Always `--dry-run` first.

## Cache invalidation & verifying changes (manual)

A WP-CLI write is persisted the moment `wp post update` returns, but caches can still serve the old version. Flush WordPress first:

```bash
ssh <ssh-user>@<wp-host> 'cd <wp-root> && wp cache flush && wp transient delete --all'
```

Then handle whatever else caches:
- **Page-cache plugins** (WP Rocket, W3 Total Cache, LiteSpeed) — `wp plugin list --status=active`. Most expose a flush command, e.g. `wp rocket clean --confirm` or `wp w3-total-cache flush all`.
- **Cloudflare** — if the official `cloudflare` plugin is active, it auto-purges the edge on post update, so a manual purge is usually unnecessary. Without it, purge the apex via the Cloudflare dashboard/API.

**Always confirm from *outside* the LAN** — the only check that proves what a visitor sees:

```bash
curl -sL --compressed "https://<domain>/?cb=$(date +%s)" | grep -i "new string"
curl -sI "https://<domain>/" | grep -i "cf-cache-status"
```

`cf-cache-status: HIT` is fine **as long as the fetched HTML already shows the new content** — it just means the edge re-cached the updated page. `HIT` with stale content means a purge is still needed.
