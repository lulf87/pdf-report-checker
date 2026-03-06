#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RUN_TESTS=true
RUN_FRONTEND_BUILD=true
COMMIT_MESSAGE=""
TARGET_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
RUN_PLAYWRIGHT=false

print_info() {
  echo "[INFO] $1"
}

print_warn() {
  echo "[WARN] $1"
}

print_error() {
  echo "[ERROR] $1" >&2
}

if [[ -f backend/.env ]]; then
  print_error "backend/.env still exists. Please delete it before publishing."
  exit 1
fi

if [[ -f .env ]]; then
  print_error ".env still exists at repo root. Please remove it before publishing."
  exit 1
fi

usage() {
  cat <<'EOF'
Usage:
  ./scripts/auto_publish.sh [--message "commit message"] [--branch target-branch] [--skip-tests] [--skip-frontend-build] [--playwright]

Options:
  --message              Commit message (quoted)
  --branch               Push target branch (default current branch)
  --skip-tests           Skip backend pytest suite
  --skip-frontend-build  Skip frontend npm build
  --playwright           Run optional playwright smoke tests (if configured)
EOF
}

while (($# > 0)); do
  case "$1" in
    --message)
      shift
      COMMIT_MESSAGE="${1:?missing --message value}"
      ;;
    --branch)
      shift
      TARGET_BRANCH="${1:?missing --branch value}"
      ;;
    --skip-tests)
      RUN_TESTS=false
      ;;
    --skip-frontend-build)
      RUN_FRONTEND_BUILD=false
      ;;
    --playwright)
      RUN_PLAYWRIGHT=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      print_error "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

if [[ -z "${COMMIT_MESSAGE}" ]]; then
  COMMIT_MESSAGE="chore(auto): update and publish $(date +'%Y%m%d-%H%M%S')"
fi

if [[ ! -d .git ]]; then
  print_error "This script must run in repository root."
  exit 1
fi

if [[ "${RUN_TESTS}" == "true" ]]; then
  print_info "Start backend validation..."
  if [[ ! -d backend/.venv ]]; then
    print_error "backend/.venv not found. Run: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
  fi
  (
    cd backend
    source .venv/bin/activate
    pytest tests/test_table_normalizer.py -v
    pytest tests/test_table_comparator.py -v
    pytest tests/ -v
  )
fi

if [[ "${RUN_FRONTEND_BUILD}" == "true" ]]; then
  print_info "Build frontend..."
  (
    cd frontend
    npm ci
    npm run build
  )
fi

if [[ "${RUN_PLAYWRIGHT}" == "true" ]]; then
  print_info "Run playwright smoke tests..."
  if command -v playwright >/dev/null 2>&1; then
    playwright test
  else
    print_warn "playwright command not found. Skip."
  fi
fi

if git status --porcelain | read -r; then
  print_info "Detected changes. Commit and push..."
  git add .
  git commit -m "$COMMIT_MESSAGE"
  git push origin "$TARGET_BRANCH"
else
  print_info "No local changes detected, nothing to commit."
fi

print_info "Auto publish completed."
