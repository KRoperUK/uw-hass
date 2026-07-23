#!/usr/bin/env bash
# Create a synthetic commit that only rewrites integration version files.
set -euo pipefail

VERSION="${1:?version required}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/write-dev-version.sh "$VERSION"

git add custom_components/utility_warehouse/manifest.json custom_components/utility_warehouse/const.py

if git diff --cached --quiet; then
  echo "error: no version file changes staged (already at ${VERSION}?)" >&2
  exit 1
fi

git -c user.name="github-actions[bot]" \
  -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit --quiet --no-verify -m "chore(dev): set version ${VERSION}"
git rev-parse HEAD
