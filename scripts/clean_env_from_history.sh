#!/usr/bin/env bash

set -euo pipefail

if [[ ! -d .git ]]; then
  echo "Not a git repository."
  exit 1
fi

if [[ -z "${1:-}" ]]; then
  TARGET_PATHS=("backend/.env")
else
  IFS=',' read -r -a TARGET_PATHS <<< "$1"
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit or stash changes first."
  echo "Current changes:"
  git status --short
  exit 1
fi

for TARGET_PATH in "${TARGET_PATHS[@]}"; do
  if [[ "$TARGET_PATH" != *.env && "$TARGET_PATH" != *.env.* ]]; then
    echo "This script is intended for env files. You passed: $TARGET_PATH"
  fi

  echo "Removing from index: $TARGET_PATH"
  git rm --cached --ignore-unmatch "$TARGET_PATH"
done

git commit -m "chore(security): remove tracked env artifact(s)" || true

for TARGET_PATH in "${TARGET_PATHS[@]}"; do
  FILTER_ARGS+=(--path "$TARGET_PATH")
done
FILTER_ARGS+=(--invert-paths --force)

if ((${#TARGET_PATHS[@]} == 0)); then
  echo "No path provided for cleanup."
  exit 1
fi

if command -v git-filter-repo >/dev/null 2>&1; then
  echo "Rewriting history with git-filter-repo..."
  git filter-repo "${FILTER_ARGS[@]}"
elif python - <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("git_filter_repo") else 1)
PY
then
  echo "git-filter-repo not in PATH, using python module..."
  python -m git_filter_repo "${FILTER_ARGS[@]}"
elif command -v git >/dev/null 2>&1; then
  echo "git-filter-repo not installed. Using git-filter-branch fallback."
  echo "If you have many refs, this is slower and not recommended."
  INDEX_FILTER_ARGS=""
  for TARGET_PATH in "${TARGET_PATHS[@]}"; do
    INDEX_FILTER_ARGS+="git rm --cached --ignore-unmatch --quiet -- '$TARGET_PATH' ; "
  done
  echo "Running fallback rewrite..."
  # shellcheck disable=SC2086
  git filter-branch --force --index-filter "$INDEX_FILTER_ARGS" --prune-empty --tag-name-filter cat -- --all
else
  echo "No git available to rewrite history."
  exit 1
fi

echo "Pushing rewritten history..."
git push origin --force --all
git push origin --force --tags

echo "If sensitive keys were exposed, rotate them immediately."
