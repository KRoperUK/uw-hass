#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?version required (e.g. 0.1.0-rc.2)}"
MANIFEST="custom_components/utility_warehouse/manifest.json"
CONST="custom_components/utility_warehouse/const.py"

if [ ! -f "$MANIFEST" ] || [ ! -f "$CONST" ]; then
  echo "error: run from repository root (missing ${MANIFEST} or ${CONST})" >&2
  exit 2
fi

if ! printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$'; then
  echo "error: invalid version string: ${VERSION}" >&2
  exit 2
fi

if ! grep -qE '"version": "' "$MANIFEST"; then
  echo "error: version field not found in ${MANIFEST}" >&2
  exit 2
fi

sed -i.bak -E "s|\"version\": \"[^\"]+\"|\"version\": \"${VERSION}\"|" "$MANIFEST"
rm -f "${MANIFEST}.bak"

if grep -qE '^VERSION = "' "$CONST"; then
  sed -i.bak -E "s|^VERSION = \"[^\"]*\"|VERSION = \"${VERSION}\"|" "$CONST"
  rm -f "${CONST}.bak"
else
  echo "error: VERSION assignment not found in ${CONST}" >&2
  exit 2
fi

echo "Wrote version ${VERSION} to ${MANIFEST} and ${CONST}" >&2
