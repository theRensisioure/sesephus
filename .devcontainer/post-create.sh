#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/sesefus"
cd "$ROOT"

echo "==> Sesefus devcontainer post-create"

# Enable the vault guard (blocks committing local-only vault data)
if [[ -f tools/guard_vaults.sh ]]; then
  git config core.hooksPath .githooks
  echo "==> vault guard enabled (core.hooksPath -> .githooks)"
fi

# Python virtualenv (kept on a Docker volume when using compose)
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install -r requirements-dev.txt

# Frontend deps
if [[ -f dashboard/ui/package.json ]]; then
  npm ci --prefix dashboard/ui || npm install --prefix dashboard/ui
fi

# Build Zig CLI (sesefus binary)
if [[ -f core/sesephus/build.zig ]]; then
  cd core/sesephus
  zig build -Doptimize=Debug
  cd "$ROOT"
  mkdir -p bin
  cp -f zig-out/bin/sesefus bin/sesefus 2>/dev/null || true
fi

# Rust dashboard (non-fatal if offline)
if [[ -f dashboard/aether-dashboard-v2/Cargo.toml ]]; then
  (
    cd dashboard/aether-dashboard-v2
    cargo build || echo "WARN: cargo build skipped (offline or missing deps)"
  )
fi

cat <<'EOF'

Sesefus devcontainer is ready.

Quick start (three terminals):
  1. Zig host:     core/sesephus/zig-out/bin/sesefus --role host
  2. Python API:   .venv/bin/python dashboard/dashboard_server.py
  3. React UI:     npm run dev --prefix dashboard/ui

URLs:
  UI        http://localhost:5173
  FastAPI   http://localhost:3001
  Zig host  http://localhost:3000

EOF