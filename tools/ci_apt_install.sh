#!/usr/bin/env bash
# Bounded apt installer for GitHub-hosted Ubuntu runners.
# The runner's Azure archive mirror can become extremely slow without
# producing a connection error, so remove it from the generated mirror list.
set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 PACKAGE [PACKAGE ...]" >&2
  exit 2
fi

MIRROR_LIST="/etc/apt/apt-mirrors.txt"
if [[ -f "$MIRROR_LIST" ]] && grep -q 'azure\.archive\.ubuntu\.com' "$MIRROR_LIST"; then
  sudo sed -i '/azure\.archive\.ubuntu\.com/d' "$MIRROR_LIST"
  echo "Disabled the degraded Azure Ubuntu mirror for this CI job."
fi

APT_OPTIONS=(
  -o Acquire::Retries=1
  -o Acquire::http::Timeout=20
  -o Acquire::https::Timeout=20
)
UPDATE_TIMEOUT="${QWASAR_CI_APT_UPDATE_TIMEOUT:-120}"
INSTALL_TIMEOUT="${QWASAR_CI_APT_INSTALL_TIMEOUT:-180}"

for attempt in 1 2; do
  if timeout --kill-after=10s "${UPDATE_TIMEOUT}s" \
      sudo apt-get update -qq "${APT_OPTIONS[@]}" &&
     timeout --kill-after=10s "${INSTALL_TIMEOUT}s" \
      sudo apt-get install -y "${APT_OPTIONS[@]}" "$@"; then
    exit 0
  fi

  if [[ "$attempt" -eq 2 ]]; then
    echo "APT update/install failed after 2 bounded attempts." >&2
    exit 1
  fi

  echo "APT mirror unavailable or too slow; retrying in 15s..." >&2
  sleep 15
done
