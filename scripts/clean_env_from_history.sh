#!/usr/bin/env bash

set -euo pipefail

if [[ ! -d .git ]]; then
  echo "Not a git repository."
  exit 1
fi

if [[ -z "${1:-}" ]]; then
  TARGET_PATH="backend/.env"
else
  TARGET_PATH="$1"
fi

if [[ "$TARGET_PATH" != *.env && "$TARGET_PATH" != *.env.* ]]; then
  echo "This script is intended for env files. You passed: $TARGET_PATH"
fi

echo "Removing from index: $TARGET_PATH"
git rm --cached --ignore-unmatch "$TARGET_PATH"
git commit -m "chore(security): remove tracked env artifact" || true

if command -v git-filter-repo >/dev/null 2>&1; then
  echo "Rewriting history with git-filter-repo..."
  git filter-repo --path "$TARGET_PATH" --invert-paths --force
elif command -v git >/dev/null 2>&1; then
  echo "git-filter-repo not installed. Using git-filter-branch fallback."
  echo "If you have many refs, this is slower and not recommended."
  echo "Running fallback rewrite for: $TARGET_PATH"
  git filter-branch --force --index-filter "git rm --cached --ignore-unmatch --quiet -- '$TARGET_PATH'" --prune-empty --tag-name-filter cat -- --all
else
  echo "No git available to rewrite history."
  exit 1
fi

echo "Pushing rewritten history..."
git push origin --force --all
git push origin --force --tags

echo "If sensitive keys were exposed, rotate them immediately."
