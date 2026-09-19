#!/usr/bin/env bash
# purge-verify.sh — after editing content, flush WordPress caches and then verify
# the change is live from OUTSIDE the LAN (the only check that proves what a real
# visitor sees). Deterministic, so SKILL.md doesn't carry the command sequence.
#
# Usage:  scripts/purge-verify.sh <public-url> ["<string that SHOULD now appear>"]
#   e.g.  scripts/purge-verify.sh https://eddykawira.com/ "AI Tooling"
#
# Env (required): WP_HOST, WP_SSH_USER, WP_ROOT
set -euo pipefail

URL="${1:-}"
EXPECT="${2:-}"
[ -n "$URL" ] || { echo "usage: $0 <public-url> [\"expected string\"]" >&2; exit 2; }
: "${WP_HOST:?set WP_HOST}"; : "${WP_SSH_USER:?set WP_SSH_USER}"; : "${WP_ROOT:?set WP_ROOT}"

OP_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
[ -S "$OP_SOCK" ] && export SSH_AUTH_SOCK="$OP_SOCK"
wp_ssh() { ssh -o StrictHostKeyChecking=accept-new "${WP_SSH_USER}@${WP_HOST}" "cd '${WP_ROOT}' && $1"; }

echo "== flush WordPress object cache + transients =="
wp_ssh "wp cache flush && wp transient delete --all"

echo "== active cache/CDN plugins (purge these too; official 'cloudflare' plugin auto-purges) =="
wp_ssh "wp plugin list --status=active --field=name" | grep -iE 'rocket|w3|litespeed|cloudflare|cache' \
  || echo "   (no page-cache/CDN plugin detected)"

echo "== cf-cache-status header =="
curl -sI "$URL" | grep -i 'cf-cache-status' || echo "   (no cf-cache-status header)"

# External cache verification is eventually-consistent — a one-shot check can
# false-negative right after a flush while the edge re-caches. Retry briefly.
echo "== external fetch + verify (cache-busted, from outside the LAN) =="
attempts="${VERIFY_ATTEMPTS:-4}"; delay="${VERIFY_DELAY:-3}"
for n in $(seq 1 "$attempts"); do
  HTML="$(curl -sL --compressed "${URL}?cb=$(date +%s)-$n")"
  if [ -z "$EXPECT" ]; then
    echo "   fetched ${#HTML} bytes (no expected string given — nothing to verify)"
    exit 0
  fi
  # here-string, not a pipe: grep -q exits early on match, which under
  # `pipefail` would SIGPIPE an upstream `printf` and falsely report no-match.
  if grep -qiF -- "$EXPECT" <<<"$HTML"; then
    echo "PASS: \"$EXPECT\" is live (attempt ${n}/${attempts}, ${#HTML} bytes)"
    exit 0
  fi
  if [ "$n" -lt "$attempts" ]; then
    echo "   attempt ${n}/${attempts}: not visible yet (${#HTML} bytes) — retrying in ${delay}s"
    sleep "$delay"
  fi
done

echo "FAIL: \"$EXPECT\" NOT in live HTML after ${attempts} attempts — edge likely still stale."
echo "      Purge the page-cache plugin / Cloudflare and re-run. (A cf-cache-status HIT is"
echo "      only OK when the fetched HTML already shows the new content.)"
exit 1
