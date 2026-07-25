#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly APP_PORT="${PORT:-8443}"
readonly SITE_CONFIG="$SCRIPT_DIR/.figma/make/site.json"

log() {
  printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
  printf '[%s] ERROR: %s\n' "$(date '+%H:%M:%S')" "$*" >&2
  exit 1
}

on_error() {
  local exit_code=$?
  printf '[%s] ERROR: Setup stopped near line %s (exit code %s).\n' \
    "$(date '+%H:%M:%S')" "${BASH_LINENO[0]:-unknown}" "$exit_code" >&2
  exit "$exit_code"
}

trap on_error ERR

cd "$SCRIPT_DIR"

log "Starting LocalChat setup in $SCRIPT_DIR"

[[ -f package.json ]] || fail "package.json was not found. Run this script from the project checkout."

log "Checking Node.js..."
command -v node >/dev/null 2>&1 || fail "Node.js is not installed. Install Node.js 22 LTS, reopen the terminal, and run this script again."

node_version="$(node -p 'process.versions.node')"
node_major="${node_version%%.*}"
node_remainder="${node_version#*.}"
node_minor="${node_remainder%%.*}"

if ! {
  [[ "$node_major" -eq 20 && "$node_minor" -ge 19 ]] ||
    [[ "$node_major" -eq 22 && "$node_minor" -ge 12 ]] ||
    [[ "$node_major" -gt 22 ]]
}; then
  fail "Node.js $node_version is unsupported. Install Node.js 20.19+ or 22.12+."
fi

log "Node.js $node_version is ready."

if command -v pnpm >/dev/null 2>&1; then
  package_runner=(pnpm)
  log "Using pnpm $(pnpm --version)."
elif command -v corepack >/dev/null 2>&1; then
  log "pnpm is not on PATH; using the Node.js Corepack copy."
  corepack pnpm --version >/dev/null
  package_runner=(corepack pnpm)
else
  fail "pnpm is unavailable. Run 'npm install -g pnpm', then run this script again."
fi

if [[ ! -f "$SITE_CONFIG" ]]; then
  log "Creating the missing local Figma site configuration..."
  mkdir -p "$(dirname "$SITE_CONFIG")"
  cat >"$SITE_CONFIG" <<'JSON'
{
  "title": "LocalChat",
  "description": "A local chatbot interface.",
  "language": "en",
  "robots": {
    "index": false
  }
}
JSON
  log "Created .figma/make/site.json."
else
  log "Local Figma site configuration already exists."
fi

log "Installing and verifying project dependencies..."
"${package_runner[@]}" install --frozen-lockfile
log "Dependencies are ready."

log "Starting the development server."
log "Open http://localhost:$APP_PORT in your browser."
log "Leave this terminal open; press Ctrl+C to stop the server."

export PORT="$APP_PORT"
exec "${package_runner[@]}" dev
