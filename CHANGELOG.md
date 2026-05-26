# Changelog

All notable changes to the `wordpress-selfhosted` skill. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). Versioning is tracked in commit
messages (no git tags).

## [1.0.5] — 2026-05-25

Applied the token-economics / progressive-disclosure method (move deterministic
logic to 0-token scripts; keep only judgment in the always-on-trigger body; push
verbose detail to an on-demand reference).

### Added
- `scripts/locate-string.sh` — deterministic string location across
  `post_content` → `wp_options` → `wp_postmeta` → active-theme files (dependencies
  excluded). Auto-detects the active theme via `wp option get stylesheet`. Reads
  `WP_HOST` / `WP_SSH_USER` / `WP_ROOT`.
- `scripts/purge-verify.sh` — flush object cache + transients, flag active
  cache/CDN plugins, then verify the change is live from **outside the LAN** with a
  retry loop (external cache verification is eventually-consistent).
- `references/editing-existing-content.md` — full manual runbook (raw queries,
  edge cases, plugin-specific flush commands), loaded on demand.

### Changed
- SKILL.md body trimmed **337 → 273 lines**. The "Editing Existing Content" and
  "Cache Invalidation & Verifying Changes" sections now carry only the reasoning
  (DB-first lookup, round-trip vs `search-replace`, why a `cf-cache-status: HIT`
  can be fine) and point to the scripts + reference for mechanics.

### Fixed
- `purge-verify.sh`: a `set -o pipefail` + `grep -q` SIGPIPE trap that made the
  external verify report a false "not found" — `grep -q` exits on first match,
  SIGPIPE-killing the upstream `printf`, whose non-zero status `pipefail` promoted
  to the pipeline. Replaced the pipe with a here-string. Caught via live testing.

### Validated
- Both scripts run live against the production host (positive + negative cases).
- Publishable surface (SKILL.md + scripts + references) passes the skill-vetting
  scanner clean (exit 0).

## [1.0.4] — 2026-05-25

### Added
- Coverage for editing **existing** content (the skill previously only documented
  creating posts): locating a string across the DB/theme, the
  get → edit-locally → update round-trip, and cache purge + external verification.

> Note: the prose runbook added here was restructured into scripts + a reference
> in 1.0.5; the capability is retained, the body is leaner.

## [1.0.3] — prior baseline

`requires.env` gating (`WP_HOST` / `WP_SSH_USER` / `WP_ROOT`),
`StrictHostKeyChecking=accept-new` as the default, and ClawHub security-scanner
hardening (Benign rating). See git history.

---

### Known follow-ups (not done)
- **Description-trigger optimization — inconclusive.** A `skill-creator`
  `run_loop` pass (model `claude-opus-4-7`, 20 queries, 60/40 split) produced no
  usable signal: the eval harness never triggered the skill for *any* query
  (uniform `0/3`, including obvious matches) because the headless `claude -p`
  proxy didn't surface the skill in that environment. The original `description`
  was retained unchanged. The frontmatter `description` is also well over the
  ~100-token progressive-disclosure target and is a candidate for trimming once a
  working triggering eval is available.
- ClawHub re-publish + re-vet of 1.0.4/1.0.5 is pending (owner action).
