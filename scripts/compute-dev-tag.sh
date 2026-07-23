#!/usr/bin/env bash
# Compute a semver pre-release version string and Git tag for a dev build.
set -euo pipefail

if [ -z "${VERSION:-}" ]; then
  echo "VERSION is required" >&2
  exit 2
fi

if [ "${HEAD_BRANCH:-}" = "main" ] && [ "${WORKFLOW_EVENT:-}" = "push" ]; then
  if [ -z "${RC_NUMBER:-}" ]; then
    echo "RC_NUMBER is required for main RC builds" >&2
    exit 2
  fi
  ver="${VERSION}-rc.${RC_NUMBER}"
  tag="v${ver}"
else
  if [ -z "${PR_NUMBER:-}" ] || [ -z "${SHORT_SHA:-}" ] || [ -z "${RUN_ID:-}" ]; then
    echo "PR_NUMBER, SHORT_SHA, and RUN_ID are required for PR builds" >&2
    exit 2
  fi
  short=$(printf '%s' "${SHORT_SHA}" | cut -c1-7)
  ver="${VERSION}-pr.${PR_NUMBER}.${short}"
  tag="v${VERSION}-pr.${PR_NUMBER}.${RUN_ID}"
fi

printf 'version=%s\n' "$ver"
printf 'tag=%s\n' "$tag"
