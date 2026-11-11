#!/usr/bin/env bash
# Development server: the app run from your files on this computer, in the
# missionboard conda environment. Code changes (CSS, JS, Python) show up on reload.
#
# Usage: bash dev.sh   → http://localhost:8002/ (and from the tablet, on the home network)
#   the family's data from data/
set -euo pipefail
cd "$(dirname "$0")"

case "${1:-}" in
  "") ;;
  -h | --help)
    sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "Unknown option: $1 (see: bash dev.sh --help)" >&2
    exit 1
    ;;
esac

port=8002
export MISSIONBOARD_DATA_DIR=data

# Activate the environment here, so it works without activating it first.
if [[ "${CONDA_DEFAULT_ENV:-}" != "missionboard" ]]; then
  if ! command -v conda >/dev/null; then
    echo "conda not found: activate the missionboard environment and try again" >&2
    exit 1
  fi
  eval "$(conda shell.bash hook)"
  set +u  # conda's activation scripts use unset variables
  conda activate missionboard
  set -u
fi

# Address of this computer on the home network, so a tablet can open it too.
lan_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "Open http://localhost:$port/ (from a tablet: http://${lan_ip:-<this computer>}:$port/)"
# 0.0.0.0: reachable from the home network, not only from this computer.
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$port"
