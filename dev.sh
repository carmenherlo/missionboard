#!/usr/bin/env bash
# Development server: the app run from your files on this computer, in the
# project's .venv (made with uv). Code changes (CSS, JS, Python) show up on reload.
#
# Usage: bash dev.sh           → http://localhost:8002/ (and from the tablet, on the home network)
#          the family's data from data/
#        bash dev.sh --fresh   → http://localhost:8003/, a brand-new installation
#          an empty data-fresh/, emptied again on every start (the voice still from data/voices/)
set -euo pipefail
cd "$(dirname "$0")"

port=8002
export MISSIONBOARD_DATA_DIR=data

case "${1:-}" in
  "") ;;
  --fresh)
    port=8003
    export MISSIONBOARD_DATA_DIR=data-fresh
    export MISSIONBOARD_VOICE_MODEL="$PWD/data/voices/es_ES-sharvard-medium.onnx"
    rm -rf data-fresh
    mkdir data-fresh
    ;;
  -h | --help)
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "Unknown option: $1 (see: bash dev.sh --help)" >&2
    exit 1
    ;;
esac

# The project's environment, so it works without activating it first.
if [[ ! -x .venv/bin/uvicorn ]]; then
  echo "No .venv: create it with" >&2
  echo "  uv venv --python 3.12 .venv && uv pip install -r requirements.txt -r requirements-dev.txt" >&2
  exit 1
fi
PATH="$PWD/.venv/bin:$PATH"

# Address of this computer on the home network, so a tablet can open it too.
lan_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "Open http://localhost:$port/ (from a tablet: http://${lan_ip:-<this computer>}:$port/)"
# 0.0.0.0: reachable from the home network, not only from this computer.
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$port"
