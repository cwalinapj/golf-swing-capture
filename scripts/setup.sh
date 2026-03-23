#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv oak-env
source oak-env/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete."
echo "Activate with: source oak-env/bin/activate"
