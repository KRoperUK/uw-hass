#!/usr/bin/env bash
# Build a HACS release asset zip of the integration package.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/custom_components/utility_warehouse"
OUT_ARG="${1:-uw.zip}"

case "${OUT_ARG}" in
  /*) OUT="${OUT_ARG}" ;;
  *) OUT="$(pwd)/${OUT_ARG}" ;;
esac

if [ ! -d "$SRC" ]; then
  echo "error: missing integration directory: ${SRC}" >&2
  exit 2
fi
if [ ! -f "${SRC}/manifest.json" ]; then
  echo "error: missing manifest.json in ${SRC}" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"

(
  cd "$SRC"
  zip -X -r -q "$OUT" . \
    -x '*__pycache__*' \
    -x '*.pyc' \
    -x '*.pyo' \
    -x '*/.DS_Store' \
    -x '.DS_Store'
)

if [ ! -f "$OUT" ]; then
  echo "error: zip was not created at ${OUT}" >&2
  exit 1
fi

echo "Wrote ${OUT} ($(wc -c <"$OUT" | tr -d ' ') bytes)"
