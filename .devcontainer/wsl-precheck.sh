#!/usr/bin/env bash
set -euo pipefail

# Runs on the host (WSL) before the container is created.
docker_cmd() {
  if command -v docker >/dev/null 2>&1; then
    docker "$@"
    return
  fi
  local win_docker="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
  if [[ -x "$win_docker" ]]; then
    "$win_docker" "$@"
    return
  fi
  return 127
}

if ! docker_cmd version >/dev/null 2>&1; then
  cat <<'EOF' >&2
ERROR: Docker is not reachable from WSL.

WSL fix:
  1. Start Docker Desktop on Windows and wait until it reports "Running".
  2. Docker Desktop → Settings → Resources → WSL Integration.
  3. Enable integration for THIS distro (e.g. Ubuntu).
  4. Restart WSL: wsl --shutdown (from PowerShell), then reopen the distro.
  5. Verify inside WSL: docker version && docker compose version

EOF
  exit 1
fi

if [[ "${LOCAL_WORKSPACE_FOLDER:-}" == /mnt/* ]]; then
  echo "WARN: Repo is on a Windows mount (${LOCAL_WORKSPACE_FOLDER})."
  echo "      Dev Containers work, but file I/O is slower than ~/projects inside WSL."
  echo "      Recommended: git clone https://github.com/Zychs/sesefus ~/projects/sesefus"
fi