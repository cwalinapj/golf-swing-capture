#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d oak-env ]]; then
  echo "Missing virtualenv. Run scripts/setup.sh first."
  exit 1
fi

source oak-env/bin/activate

OUT_DIR="${OUT_DIR:-/Volumes/Torrents/golf_takes}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

MONO_EXPOSURE_US="${MONO_EXPOSURE_US:-120}"
MONO_ISO="${MONO_ISO:-400}"
RGB_EXPOSURE_US="${RGB_EXPOSURE_US:-120}"
RGB_ISO="${RGB_ISO:-200}"
RGB_FOCUS="${RGB_FOCUS:-120}"

ARGS=(
  --out "$OUT_DIR"
  --host "$HOST"
  --port "$PORT"
  --mono-exposure-us "$MONO_EXPOSURE_US"
  --mono-iso "$MONO_ISO"
  --rgb-exposure-us "$RGB_EXPOSURE_US"
  --rgb-iso "$RGB_ISO"
  --rgb-focus "$RGB_FOCUS"
)

if [[ -n "${DEVICE_ID:-}" ]]; then
  ARGS+=(--device-id "$DEVICE_ID")
fi

if [[ "${NO_RGB:-0}" == "1" ]]; then
  ARGS+=(--no-rgb)
fi

python app.py "${ARGS[@]}"
