#!/usr/bin/env bash
set -euo pipefail
SOURCE_HTML="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET_HTML="${1:-/var/www/vhosts/uadia.fr/cercle.uadia.fr/main/src/html}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TARGET_HTML"
[[ -f "$TARGET_HTML/Ananke.html" ]] && cp -a "$TARGET_HTML/Ananke.html" "$TARGET_HTML/Ananke.html.backup-$STAMP"
[[ -d "$TARGET_HTML/AnankeAI" ]] && mv "$TARGET_HTML/AnankeAI" "$TARGET_HTML/AnankeAI.backup-$STAMP"
cp -a "$SOURCE_HTML/Ananke.html" "$TARGET_HTML/Ananke.html"
cp -a "$SOURCE_HTML/AnankeAI" "$TARGET_HTML/AnankeAI"
"$TARGET_HTML/AnankeAI/scripts/permissions.sh" "$TARGET_HTML/AnankeAI"
echo "ANANKÉ installée dans $TARGET_HTML sans service HTTP local."
