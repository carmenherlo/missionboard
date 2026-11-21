#!/usr/bin/env bash
# One folder per agent: a git worktree next to the project, on its own branch,
# with its own .venv and its own port for browser tests.
#
# Usage: bash tools/worktree.sh new <task>     → ../missionboard2-<task>, branch <task>
#        bash tools/worktree.sh list           → the worktrees and their ports
#        bash tools/worktree.sh remove <task>  → deletes the folder (the branch only if merged)
#
# The local files that are not in git (docs/, CLAUDE.local.md) are linked from
# the main folder, so every agent reads the same plan and private notes.
set -euo pipefail

main="$(cd "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")" && pwd)"
name="$(basename "$main")"
first_port=8011
last_port=8019

usage() { sed -n '5,7p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

free_port() {
  local used port
  used="$(cat "$main"/../"$name"-*/.agent-port 2>/dev/null || true)"
  for ((port = first_port; port <= last_port; port++)); do
    grep -qx "$port" <<<"$used" && continue
    ss -ltn "sport = :$port" | grep -q LISTEN && continue
    echo "$port"
    return
  done
  echo "No free port between $first_port and $last_port" >&2
  exit 1
}

new() {
  local task="$1" dir="$main/../$name-$1"
  [[ -e "$dir" ]] && { echo "$dir already exists" >&2; exit 1; }
  git -C "$main" worktree add --quiet "$dir" -b "$task" main
  dir="$(cd "$dir" && pwd)"
  ln -s "$main/docs" "$dir/docs"
  ln -s "$main/CLAUDE.local.md" "$dir/CLAUDE.local.md"
  free_port >"$dir/.agent-port"
  (cd "$dir" && uv venv --quiet --python 3.12 .venv &&
    uv pip install --quiet --python .venv/bin/python -r requirements.txt -r requirements-dev.txt)
  echo
  echo "Ready: $dir (branch $task, test port $(cat "$dir/.agent-port"))"
  echo "Open Claude Code there:  cd $dir && claude"
}

list() {
  git -C "$main" worktree list
  for f in "$main"/../"$name"-*/.agent-port; do
    [[ -f "$f" ]] && echo "$(basename "$(dirname "$f")"): port $(cat "$f")"
  done
}

remove() {
  local task="$1" dir="$main/../$name-$1"
  git -C "$main" worktree remove "$dir"
  git -C "$main" branch -d "$task" || echo "Branch $task kept: it is not merged into main yet."
}

case "${1:-}" in
  new) [[ -n "${2:-}" ]] || usage 1; new "$2" ;;
  list) list ;;
  remove) [[ -n "${2:-}" ]] || usage 1; remove "$2" ;;
  -h | --help | "") usage ;;
  *) usage 1 ;;
esac
