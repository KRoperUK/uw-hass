#!/usr/bin/env bash
# Print the next main-branch RC number for a given version.
set -euo pipefail

VERSION="${1:?version required (e.g. 0.1.0)}"

if [ -z "${GITHUB_REPOSITORY:-}" ]; then
  echo "GITHUB_REPOSITORY is required" >&2
  exit 2
fi

version_re=$(printf '%s' "${VERSION}" | sed 's/\./\\./g')
pattern="^(dev-)?v${version_re}-rc\\.[0-9]+$"

collect_rc_numbers() {
  {
    gh release list --limit 1000 --json tagName --jq '.[].tagName' 2>/dev/null || true
    gh api "repos/${GITHUB_REPOSITORY}/git/matching-refs/tags/v${VERSION}-rc." \
      --paginate --jq '.[].ref' 2>/dev/null \
      | sed 's#^refs/tags/##' || true
    gh api "repos/${GITHUB_REPOSITORY}/git/matching-refs/tags/dev-v${VERSION}-rc." \
      --paginate --jq '.[].ref' 2>/dev/null \
      | sed 's#^refs/tags/##' || true
  } | grep -E "${pattern}" | sed -E 's/^.*-rc\.//' | grep -E '^[0-9]+$' || true
}

highest=$(collect_rc_numbers | sort -n | tail -1 || true)
printf '%s\n' "$((${highest:-0} + 1))"
