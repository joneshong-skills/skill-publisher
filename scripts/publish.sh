#!/usr/bin/env bash
# publish.sh — Deterministic git + platform registration for skill-publisher
# Usage:
#   publish.sh <skill-name> [--dry-run] [--skip-logo] [--skip-register]
#   publish.sh --scan [--json]

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
GITHUB_ORG="joneshong-skills"

# ── Color helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
err()  { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
info() { echo -e "${CYAN}[INFO]${RESET}  $*"; }
dry()  { echo -e "${YELLOW}[DRY-RUN]${RESET} $*"; }

# ── Argument parsing ─────────────────────────────────────────────────────────
SKILL_NAME=""
DRY_RUN=0
SKIP_LOGO=0
SKIP_REGISTER=0
SCAN_MODE=0
JSON_FLAG=""

for arg in "$@"; do
  case "$arg" in
    --dry-run)       DRY_RUN=1 ;;
    --skip-logo)     SKIP_LOGO=1 ;;
    --skip-register) SKIP_REGISTER=1 ;;
    --scan)          SCAN_MODE=1 ;;
    --json)          JSON_FLAG="--json" ;;
    --*)
      err "Unknown flag: $arg"
      exit 1
      ;;
    *)
      if [[ -z "$SKILL_NAME" ]]; then
        SKILL_NAME="$arg"
      else
        err "Unexpected positional argument: $arg"
        exit 1
      fi
      ;;
  esac
done

# ── --scan mode ───────────────────────────────────────────────────────────────
if [[ "$SCAN_MODE" -eq 1 ]]; then
  SCAN_SCRIPT="${SCRIPT_DIR}/scan_status.py"
  if [[ ! -f "$SCAN_SCRIPT" ]]; then
    err "scan_status.py not found at: $SCAN_SCRIPT"
    exit 1
  fi
  python3 "$SCAN_SCRIPT" ${JSON_FLAG}
  exit $?
fi

# ── Require skill name ────────────────────────────────────────────────────────
if [[ -z "$SKILL_NAME" ]]; then
  echo -e "${BOLD}Usage:${RESET}"
  echo "  $(basename "$0") <skill-name> [--dry-run] [--skip-logo] [--skip-register]"
  echo "  $(basename "$0") --scan [--json]"
  exit 1
fi

SKILL_DIR="${SKILLS_DIR}/${SKILL_NAME}"

echo ""
echo -e "${BOLD}=== Skill Publisher: ${SKILL_NAME} ===${RESET}"
[[ "$DRY_RUN" -eq 1 ]] && echo -e "${YELLOW}DRY-RUN mode — no changes will be made${RESET}"
echo ""

# ── Step 1: Validate skill directory ─────────────────────────────────────────
info "Validating skill directory..."
if [[ ! -d "$SKILL_DIR" ]]; then
  err "Skill directory not found: $SKILL_DIR"
  exit 1
fi
ok "Skill directory exists: $SKILL_DIR"

# ── Step 2: Check required files ─────────────────────────────────────────────
info "Checking required files..."

ABORT=0

if [[ ! -f "${SKILL_DIR}/SKILL.md" ]]; then
  err "SKILL.md is required but missing."
  ABORT=1
else
  ok "SKILL.md found"
fi

if [[ ! -f "${SKILL_DIR}/README.md" ]]; then
  err "README.md is required but missing. Run /skill-publisher to generate it first."
  ABORT=1
else
  ok "README.md found"
fi

if [[ ! -f "${SKILL_DIR}/README.zh.md" ]]; then
  warn "README.zh.md is missing (recommended). Continuing without it."
else
  ok "README.zh.md found"
fi

if [[ "$SKIP_LOGO" -eq 0 ]] && [[ ! -f "${SKILL_DIR}/logo.png" ]]; then
  warn "logo.png not found. Use --skip-logo to suppress this warning, or run /image-gen to create one."
else
  [[ -f "${SKILL_DIR}/logo.png" ]] && ok "logo.png found"
fi

if [[ "$ABORT" -eq 1 ]]; then
  err "Pre-flight checks failed. Aborting."
  exit 1
fi

# ── Step 3: Initialize git repo ───────────────────────────────────────────────
info "Checking git repository..."

if [[ ! -d "${SKILL_DIR}/.git" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would run: git -C \"$SKILL_DIR\" init && git -C \"$SKILL_DIR\" checkout -b main"
  else
    git -C "$SKILL_DIR" init -q
    # Ensure branch is named 'main'
    git -C "$SKILL_DIR" checkout -b main -q 2>/dev/null || true
    ok "Initialized git repository"
  fi
else
  ok "Git repository already initialized"
fi

# ── Step 4: Create .gitignore ─────────────────────────────────────────────────
GITIGNORE_PATH="${SKILL_DIR}/.gitignore"
GITIGNORE_CONTENT="__pycache__/
*.pyc
*.pyo
.DS_Store
observations.md
lessons.md
*.egg-info/
.env
"

info "Checking .gitignore..."
if [[ ! -f "$GITIGNORE_PATH" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would create .gitignore with standard patterns"
  else
    printf '%s' "$GITIGNORE_CONTENT" > "$GITIGNORE_PATH"
    ok "Created .gitignore"
  fi
else
  ok ".gitignore already exists"
fi

# ── Step 5: Create LICENSE if missing ────────────────────────────────────────
LICENSE_PATH="${SKILL_DIR}/LICENSE"
CURRENT_YEAR="$(date +%Y)"
MIT_LICENSE="MIT License

Copyright (c) ${CURRENT_YEAR} joneshong-skills

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"

info "Checking LICENSE..."
if [[ ! -f "$LICENSE_PATH" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would create MIT LICENSE"
  else
    printf '%s' "$MIT_LICENSE" > "$LICENSE_PATH"
    ok "Created MIT LICENSE"
  fi
else
  ok "LICENSE already exists"
fi

# ── Step 6: Stage files ───────────────────────────────────────────────────────
info "Staging files..."

# Build list of files/dirs to stage (only those that actually exist)
STAGE_TARGETS=()
for target in SKILL.md README.md README.zh.md logo.png .gitignore LICENSE; do
  [[ -e "${SKILL_DIR}/${target}" ]] && STAGE_TARGETS+=("$target")
done
for dir in assets scripts references; do
  [[ -d "${SKILL_DIR}/${dir}" ]] && STAGE_TARGETS+=("$dir")
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  dry "Would stage: ${STAGE_TARGETS[*]}"
else
  git -C "$SKILL_DIR" add -- "${STAGE_TARGETS[@]}" 2>/dev/null || true
  ok "Staged: ${STAGE_TARGETS[*]}"
fi

# ── Step 7: Commit ────────────────────────────────────────────────────────────
info "Preparing commit..."

# Detect if there's a prior commit
HAS_COMMITS=0
git -C "$SKILL_DIR" rev-parse HEAD >/dev/null 2>&1 && HAS_COMMITS=1 || true

if [[ "$HAS_COMMITS" -eq 0 ]]; then
  COMMIT_MSG="Publish skill: ${SKILL_NAME}"
else
  COMMIT_MSG="Update skill: ${SKILL_NAME}"
fi

# Check if there's anything to commit
STAGED_COUNT=0
STAGED_COUNT=$(git -C "$SKILL_DIR" diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ') || true

if [[ "$STAGED_COUNT" -eq 0 ]]; then
  warn "Nothing to commit — working tree is clean."
else
  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would commit: \"$COMMIT_MSG\""
    dry "Files to commit:"
    git -C "$SKILL_DIR" diff --cached --name-only 2>/dev/null | while read -r f; do
      dry "  + $f"
    done
  else
    git -C "$SKILL_DIR" commit -m "$COMMIT_MSG" -q
    ok "Committed: \"$COMMIT_MSG\""
  fi
fi

# ── Step 8: Check / create GitHub repo ───────────────────────────────────────
echo ""
info "Checking GitHub repo: ${GITHUB_ORG}/${SKILL_NAME}..."

REPO_EXISTS=0
gh repo view "${GITHUB_ORG}/${SKILL_NAME}" --json name >/dev/null 2>&1 && REPO_EXISTS=1 || true

if [[ "$REPO_EXISTS" -eq 0 ]]; then
  warn "GitHub repo does not exist: ${GITHUB_ORG}/${SKILL_NAME}"
  CREATE_CMD="gh repo create ${GITHUB_ORG}/${SKILL_NAME} --public --source=\"${SKILL_DIR}\" --remote=origin --push"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would create new repo and push:"
    dry "  $CREATE_CMD"
  else
    echo ""
    echo -e "${BOLD}Command to execute:${RESET}"
    echo "  $CREATE_CMD"
    echo ""
    printf "Proceed? [y/N] "
    read -r CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
      if gh repo create "${GITHUB_ORG}/${SKILL_NAME}" --public --source="${SKILL_DIR}" --remote=origin --push; then
        ok "Repo created and pushed: https://github.com/${GITHUB_ORG}/${SKILL_NAME}"
      else
        err "Failed to create repo. Check gh auth status."
        exit 1
      fi
    else
      warn "Skipped repo creation."
    fi
  fi
else
  ok "GitHub repo exists: https://github.com/${GITHUB_ORG}/${SKILL_NAME}"

  # Ensure remote is set
  REMOTE_URL="https://github.com/${GITHUB_ORG}/${SKILL_NAME}.git"
  CURRENT_REMOTE=$(git -C "$SKILL_DIR" remote get-url origin 2>/dev/null) || CURRENT_REMOTE=""

  if [[ -z "$CURRENT_REMOTE" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      dry "Would add remote: git remote add origin $REMOTE_URL"
    else
      git -C "$SKILL_DIR" remote add origin "$REMOTE_URL" 2>/dev/null || true
      ok "Remote origin added"
    fi
  fi

  PUSH_CMD="git -C \"${SKILL_DIR}\" push -u origin main"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would push to existing repo:"
    dry "  $PUSH_CMD"
  else
    echo ""
    echo -e "${BOLD}Command to execute:${RESET}"
    echo "  git push -u origin main  (in ${SKILL_DIR})"
    echo ""
    printf "Proceed? [y/N] "
    read -r CONFIRM
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
      if git -C "$SKILL_DIR" push -u origin main; then
        ok "Pushed to: https://github.com/${GITHUB_ORG}/${SKILL_NAME}"
      else
        err "Push failed. Check your git remote and credentials."
        exit 1
      fi
    else
      warn "Skipped push."
    fi
  fi
fi

# ── Step 9: Platform registration ────────────────────────────────────────────
if [[ "$SKIP_REGISTER" -eq 0 ]]; then
  echo ""
  info "Registering on platforms..."

  DEEPWIKI_URL="https://deepwiki.com/${GITHUB_ORG}/${SKILL_NAME}"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    dry "Would trigger DeepWiki indexing: curl -s \"$DEEPWIKI_URL\""
    dry "Would print Context7 manual submission note"
  else
    info "Triggering DeepWiki indexing: $DEEPWIKI_URL"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$DEEPWIKI_URL") || HTTP_STATUS="000"
    if [[ "$HTTP_STATUS" =~ ^[23] ]]; then
      ok "DeepWiki triggered (HTTP $HTTP_STATUS): $DEEPWIKI_URL"
    else
      warn "DeepWiki returned HTTP $HTTP_STATUS — indexing may take a few minutes."
    fi

    echo ""
    echo -e "${YELLOW}[Context7]${RESET} Manual submission required:"
    echo "  1. Visit: https://context7.com/"
    echo "  2. Submit: https://github.com/${GITHUB_ORG}/${SKILL_NAME}"
    echo "  Or use MCP: mcp__context7__resolve-library-id with libraryName=\"${SKILL_NAME}\""
  fi
else
  info "Skipping platform registration (--skip-register)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}=== Done: ${SKILL_NAME} ===${RESET}"
if [[ "$DRY_RUN" -eq 0 ]]; then
  echo -e "  GitHub : https://github.com/${GITHUB_ORG}/${SKILL_NAME}"
  echo -e "  DeepWiki: https://deepwiki.com/${GITHUB_ORG}/${SKILL_NAME}"
fi
echo ""
