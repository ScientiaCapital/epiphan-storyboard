#!/usr/bin/env bash
set -euo pipefail

echo "==> epiphan-storyboard init"

if [ ! -f .env ]; then
  echo "WARNING: .env not found — copy .env.example and fill in values"
fi

echo "==> Creating virtual environment"
python3 -m venv .venv

echo "==> Installing dependencies"
.venv/bin/pip install -e ".[dev]"

echo "==> Done. Activate with: source .venv/bin/activate"
echo "==> Run dev server: uvicorn src.api:app --reload"
