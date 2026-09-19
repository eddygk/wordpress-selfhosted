#!/usr/bin/env bash
# create-post.sh — create a post or page from a local Gutenberg HTML file.
# Wraps `wp post create` over SSH (deterministic). Prints the new post ID.
#
# Usage: scripts/create-post.sh --file <local.html> --title "<title>" \
#          [--type post|page] [--status draft|pending|publish] [--author <user-id>]
#
# Env (required): WP_HOST, WP_SSH_USER, WP_ROOT
set -euo pipefail

FILE="" TITLE="" TYPE="post" STATUS="draft" AUTHOR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --file)   FILE="$2";   shift 2 ;;
    --title)  TITLE="$2";  shift 2 ;;
    --type)   TYPE="$2";   shift 2 ;;
    --status) STATUS="$2"; shift 2 ;;
    --author) AUTHOR="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
{ [ -n "$FILE" ] && [ -f "$FILE" ]; } || { echo "usage: $0 --file <local.html> --title \"...\" [--type post|page] [--status draft] [--author <id>]" >&2; exit 2; }
[ -n "$TITLE" ] || { echo "--title is required" >&2; exit 2; }

# Pre-flight validation: verify Gutenberg blocks, title, and RFC/security sanitization
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_BIN="python3"
command -v python3 >/dev/null 2>&1 || PY_BIN="python"

"${PY_BIN}" "${SCRIPT_DIR}/validate-gutenberg.py" "$FILE" || exit 1
"${PY_BIN}" "${SCRIPT_DIR}/validate-sanitization.py" "$FILE" || exit 1
echo "$TITLE" | "${PY_BIN}" "${SCRIPT_DIR}/validate-sanitization.py" - || exit 1

: "${WP_HOST:?set WP_HOST}"; : "${WP_SSH_USER:?set WP_SSH_USER}"; : "${WP_ROOT:?set WP_ROOT}"

OP_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
[ -S "$OP_SOCK" ] && export SSH_AUTH_SOCK="$OP_SOCK"
SSHO=(-o StrictHostKeyChecking=accept-new); HOST="${WP_SSH_USER}@${WP_HOST}"

# Upload the content body to a temp file, create from it, then remove the temp.
REMOTE="/tmp/create-post-$$.html"
scp "${SSHO[@]}" "$FILE" "${HOST}:${REMOTE}" >/dev/null
AUTHOR_ARG=""; [ -n "$AUTHOR" ] && AUTHOR_ARG="--post_author=${AUTHOR}"
ID=$(ssh "${SSHO[@]}" "$HOST" "cd '${WP_ROOT}' && wp post create '${REMOTE}' --post_title=\"${TITLE}\" --post_type='${TYPE}' --post_status='${STATUS}' ${AUTHOR_ARG} --porcelain; rm -f '${REMOTE}'")
[ -n "$ID" ] || { echo "post creation failed (no ID returned)" >&2; exit 1; }
echo "$ID"
