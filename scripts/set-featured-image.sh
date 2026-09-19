#!/usr/bin/env bash
# set-featured-image.sh — upload a local image, import it to the media library,
# and set it as a post's featured image (thumbnail). Deterministic.
#
# Usage: scripts/set-featured-image.sh <post-id> <local-image> ["<media title>"]
#
# Env (required): WP_HOST, WP_SSH_USER, WP_ROOT
set -euo pipefail

ID="${1:-}"; IMG="${2:-}"; TITLE="${3:-}"
{ [ -n "$ID" ] && [ -n "$IMG" ] && [ -f "$IMG" ]; } || { echo "usage: $0 <post-id> <local-image> [\"media title\"]" >&2; exit 2; }
: "${WP_HOST:?set WP_HOST}"; : "${WP_SSH_USER:?set WP_SSH_USER}"; : "${WP_ROOT:?set WP_ROOT}"

OP_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
[ -S "$OP_SOCK" ] && export SSH_AUTH_SOCK="$OP_SOCK"
SSHO=(-o StrictHostKeyChecking=accept-new); HOST="${WP_SSH_USER}@${WP_HOST}"

REMOTE="/tmp/featured-$$-$(basename "$IMG")"
scp "${SSHO[@]}" "$IMG" "${HOST}:${REMOTE}" >/dev/null
TITLE_ARG=""; [ -n "$TITLE" ] && TITLE_ARG="--title=\"${TITLE}\""
ATTACH=$(ssh "${SSHO[@]}" "$HOST" "cd '${WP_ROOT}' && wp media import '${REMOTE}' ${TITLE_ARG} --porcelain; rm -f '${REMOTE}'")
[ -n "$ATTACH" ] || { echo "media import failed (no attachment ID)" >&2; exit 1; }
ssh "${SSHO[@]}" "$HOST" "cd '${WP_ROOT}' && wp post meta update ${ID} _thumbnail_id ${ATTACH}"
echo "attachment ${ATTACH} set as featured image on post ${ID}"
