#!/usr/bin/env bash
# Push secrets to the Railway API service without ever echoing them.
# Reads the keys that already exist in virtual-closet/.env; generates APP_SECRET
# once and saves it to server/.app_secret (gitignored) so the frontend can reuse it.
#
# Usage:  ./scripts/set_railway_vars.sh [service-name]
# Run from ~/wardrobe-v3/server, after `railway login` + `railway init` + `railway add`.

set -euo pipefail

SERVICE="${1:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ENV="$HERE/../virtual-closet/.env"
SECRET_FILE="$HERE/.app_secret"

[ -f "$SRC_ENV" ] || { echo "!! no $SRC_ENV — nothing to read keys from"; exit 1; }

# Pull the two keys we forward. `set -a` + source would leak everything; grep just these.
FAL_KEY="$(grep -E '^FAL_KEY=' "$SRC_ENV" | head -1 | cut -d= -f2-)"
ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' "$SRC_ENV" | head -1 | cut -d= -f2-)"

# APP_SECRET: generate once, then reuse. Rotating it invalidates the frontend token.
if [ -f "$SECRET_FILE" ]; then
  APP_SECRET="$(cat "$SECRET_FILE")"
  echo "using existing APP_SECRET from $SECRET_FILE"
else
  APP_SECRET="$(openssl rand -hex 24)"
  printf '%s' "$APP_SECRET" > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
  echo "generated APP_SECRET -> $SECRET_FILE (keep this; the frontend sends it)"
fi

args=(variables)
[ -n "$SERVICE" ] && args+=(--service "$SERVICE")
args+=(
  --set "APP_SECRET=$APP_SECRET"
  --set "BUDGET_CAP_USD=45"
  --set "FAL_KEY=$FAL_KEY"
  --set "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
  --set "R2_BUCKET=virtual-closet"
)

railway "${args[@]}"
echo "done — set APP_SECRET, BUDGET_CAP_USD=45, FAL_KEY, ANTHROPIC_API_KEY, R2_BUCKET"
echo "still to set by hand (step 5): DATABASE_URL reference + the three R2_* credentials"
