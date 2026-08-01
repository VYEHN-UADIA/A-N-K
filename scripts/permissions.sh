#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/var/www/vhosts/uadia.fr/cercle.uadia.fr/main/src/html/AnankeAI}"
mkdir -p "$ROOT/state/uploads" "$ROOT/state/analyses"
find "$ROOT" -type d -exec chmod 750 {} +
find "$ROOT" -type f -exec chmod 640 {} +
chmod 750 "$ROOT/scripts" "$ROOT/state" "$ROOT/state/uploads" "$ROOT/state/analyses"
chmod 750 "$ROOT/scripts/permissions.sh" "$ROOT/scripts/install.sh" 2>/dev/null || true
chmod 750 "$ROOT/Ananke_runtime.py" 2>/dev/null || true
if [[ -f "$ROOT/state/ananke.sqlite3" ]]; then chmod 660 "$ROOT/state/ananke.sqlite3"; fi
