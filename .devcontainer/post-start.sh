#!/usr/bin/env bash
set -euo pipefail

# Detect WSL bind-mount from Windows filesystem (/mnt/c, /mnt/d, ...)
if grep -qs ' /workspaces/sesefus ' /proc/mounts; then
  if grep -qs ' /workspaces/sesefus .*drvfs\|9p' /proc/mounts 2>/dev/null \
     || [[ "${LOCAL_WORKSPACE_FOLDER:-}" == /mnt/* ]]; then
    echo "NOTE: Workspace appears to be on a Windows mount (e.g. /mnt/c)."
    echo "      For faster I/O, clone the repo into ~/projects/sesefus inside WSL."
  fi
fi

# WSLg / PulseAudio passthrough for audio_input_layer experiments
if [[ -n "${PULSE_SERVER:-}" ]] || [[ -S /mnt/wslg/runtime-dir/pulse/native ]]; then
  export PULSE_SERVER="${PULSE_SERVER:-unix:/mnt/wslg/runtime-dir/pulse/native}"
  echo "Audio: PULSE_SERVER=${PULSE_SERVER}"
else
  echo "Audio: no PulseAudio socket detected; audio capture may be simulated inside the container."
fi