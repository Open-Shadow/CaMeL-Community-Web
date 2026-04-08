#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/4] Backend targeted full-flow tests"
cd "$ROOT_DIR/backend"
uv run pytest -q \
  tests/test_admin_skill_review_api.py \
  tests/test_skills_api_flow.py \
  tests/test_bounty_api_flow.py \
  tests/test_workshop_service.py

echo "[2/4] Backend full regression"
uv run pytest -q

echo "[3/4] Frontend type check"
cd "$ROOT_DIR/frontend"
pnpm -s run type-check

echo "[4/4] Frontend production build"
pnpm -s run build

echo "All full-flow checks passed."
