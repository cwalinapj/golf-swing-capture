#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export OUT_DIR="${OUT_DIR:-/Volumes/Torrents/golf_takes}"

# Impact-zone defaults
export MONO_EXPOSURE_US="${MONO_EXPOSURE_US:-120}"
export MONO_ISO="${MONO_ISO:-400}"

# Context RGB defaults
export RGB_EXPOSURE_US="${RGB_EXPOSURE_US:-120}"
export RGB_ISO="${RGB_ISO:-200}"
export RGB_FOCUS="${RGB_FOCUS:-120}"

exec "$ROOT_DIR/scripts/run.sh"
