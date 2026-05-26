#!/usr/bin/env bash
# set-post-meta.sh — set taxonomy + SEO meta on an existing post/page (deterministic).
#
# Usage: scripts/set-post-meta.sh <post-id> [--category <slug>] [--tags "<t1> <t2> ..."] \
#          [--metadesc "<120-155 chars>"] [--focuskw "<keyphrase>"]
#   --tags takes a single space-separated string. Yoast field names are used for
#   --metadesc / --focuskw (Rank Math users: edit the meta_key in this script).
#
# Env (required): WP_HOST, WP_SSH_USER, WP_ROOT
set -euo pipefail

ID="${1:-}"; shift || true
[ -n "$ID" ] || { echo "usage: $0 <post-id> [--category slug] [--tags \"a b\"] [--metadesc \"...\"] [--focuskw \"...\"]" >&2; exit 2; }

CATEGORY="" TAGS="" METADESC="" FOCUSKW=""
while [ $# -gt 0 ]; do
  case "$1" in
    --category) CATEGORY="$2"; shift 2 ;;
    --tags)     TAGS="$2";     shift 2 ;;
    --metadesc) METADESC="$2"; shift 2 ;;
    --focuskw)  FOCUSKW="$2";  shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
: "${WP_HOST:?set WP_HOST}"; : "${WP_SSH_USER:?set WP_SSH_USER}"; : "${WP_ROOT:?set WP_ROOT}"

OP_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
[ -S "$OP_SOCK" ] && export SSH_AUTH_SOCK="$OP_SOCK"
wp_ssh() { ssh -o StrictHostKeyChecking=accept-new "${WP_SSH_USER}@${WP_HOST}" "cd '${WP_ROOT}' && $1"; }

[ -n "$CATEGORY" ] && { echo "→ category: $CATEGORY";   wp_ssh "wp post term set ${ID} category '${CATEGORY}'"; }
[ -n "$TAGS" ]     && { echo "→ tags: $TAGS";           wp_ssh "wp post term set ${ID} post_tag ${TAGS}"; }
[ -n "$METADESC" ] && { echo "→ meta description set";  wp_ssh "wp post meta update ${ID} _yoast_wpseo_metadesc \"${METADESC}\""; }
[ -n "$FOCUSKW" ]  && { echo "→ focus keyphrase: $FOCUSKW"; wp_ssh "wp post meta update ${ID} _yoast_wpseo_focuskw \"${FOCUSKW}\""; }
echo "done (post ${ID})."
