#!/usr/bin/env bash
# locate-string.sh — find where a visible string lives in a WordPress install,
# checking the places it most commonly lives, cheapest/most-common first:
#   1. post_content (pages/posts)  2. wp_options  3. wp_postmeta  4. theme files
#
# Deterministic discovery, so SKILL.md doesn't have to carry the query syntax
# (runs at 0 token cost — see references/editing-existing-content.md for the
# manual equivalent and edge cases).
#
# Usage:  scripts/locate-string.sh "<distinctive fragment>"
#   Use a SHORT, distinctive middle chunk — not a whole line. Separators (| ·),
#   HTML entities (&amp;) and smart quotes differ between rendered and stored
#   text, so matching the entire string often fails. Avoid double-quotes/backticks
#   in the fragment.
#
# Env (required): WP_HOST, WP_SSH_USER, WP_ROOT
# Env (optional): WP_THEME  (active theme dir; auto-detected via `wp option get stylesheet`)
set -euo pipefail

FRAGMENT="${1:-}"
[ -n "$FRAGMENT" ] || { echo "usage: $0 \"<distinctive fragment>\"" >&2; exit 2; }
: "${WP_HOST:?set WP_HOST}"; : "${WP_SSH_USER:?set WP_SSH_USER}"; : "${WP_ROOT:?set WP_ROOT}"

# macOS 1Password SSH agent needs its socket; elsewhere use the inherited agent.
OP_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
[ -S "$OP_SOCK" ] && export SSH_AUTH_SOCK="$OP_SOCK"

wp_ssh() { ssh -o StrictHostKeyChecking=accept-new "${WP_SSH_USER}@${WP_HOST}" "cd '${WP_ROOT}' && $1"; }

# Double single-quotes so the fragment is safe inside the SQL LIKE literal.
sql=${FRAGMENT//\'/\'\'}

echo "== 1. post_content (pages/posts) — most user-visible copy, incl. raw HTML in pages =="
wp_ssh "wp db query \"SELECT ID, post_title, post_type, post_status FROM wp_posts WHERE post_content LIKE '%${sql}%'\"" || true

echo "== 2. wp_options — site title, tagline, widgets, theme mods, plugin config =="
wp_ssh "wp db query \"SELECT option_id, option_name FROM wp_options WHERE option_value LIKE '%${sql}%'\"" || true

echo "== 3. wp_postmeta — ACF, page-builder payloads, SEO (Yoast/Rank Math) =="
wp_ssh "wp db query \"SELECT meta_id, post_id, meta_key FROM wp_postmeta WHERE meta_value LIKE '%${sql}%'\"" || true

echo "== 4. active theme files (only if not in the DB; deps excluded) =="
THEME="${WP_THEME:-$(wp_ssh 'wp option get stylesheet' 2>/dev/null || true)}"
if [ -n "$THEME" ]; then
  echo "   theme: $THEME"
  wp_ssh "cd wp-content/themes/'${THEME}' && grep -rni '${FRAGMENT}' . --include='*.php' --include='*.blade.php' --include='*.js' | grep -vE 'node_modules|/vendor/' || echo '   (no theme-file matches)'" || true
else
  echo "   (could not determine active theme; set WP_THEME to grep theme files)"
fi

echo
echo "Found it in post_content? Edit in place: scripts/... (see Edit post content in place)."
echo "Only in a compiled bundle under public/ or dist/ (not resources/)? It's built at"
echo "build time — fix the source and rebuild (npm run build / yarn build), not the bundle."
