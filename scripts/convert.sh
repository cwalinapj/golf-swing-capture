#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d oak-env ]]; then
  echo "Missing virtualenv. Run scripts/setup.sh first."
  exit 1
fi

source oak-env/bin/activate
python -m capture.converter "$@"
