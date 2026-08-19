#!/usr/bin/env python3
"""publish.py — Deterministic git + platform registration for skill-publisher

Usage:
  publish.py <skill-name> [--dry-run] [--skip-logo] [--register-note]
  publish.py --scan [--json]
"""

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = Path.home() / ".claude" / "skills"
GITHUB_ORG = "joneshong-skills"

# ── Color helpers ─────────────────────────────────────────────────────────────
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg):
    print(f"{GREEN}[OK]{RESET}    {msg}")


def warn(msg):
    print(f"{YELLOW}[WARN]{RESET}  {msg}")


def err(msg):
    print(f"{RED}[ERROR]{RESET} {msg}", file=sys.stderr)


def info(msg):
    print(f"{CYAN}[INFO]{RESET}  {msg}")


def dry(msg):
    print(f"{YELLOW}[DRY-RUN]{RESET} {msg}")


def run_git(
    args: list, cwd: str = None, capture: bool = True
) -> subprocess.CompletedProcess:
    cmd = ["git"]
    if cwd:
        cmd += ["-C", cwd]
    cmd += args
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    else:
        return subprocess.run(cmd)


GITIGNORE_CONTENT = """\
__pycache__/
*.pyc
*.pyo
.DS_Store
observations.md
lessons.md
*.egg-info/
.env
"""

MIT_LICENSE_TEMPLATE = """\
MIT License

Copyright (c) {year} joneshong-skills

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def preflight_secrets_pii(skill_dir):
    """Fail-closed secrets + personal-path/PII scan run before any git action."""
    info("Running secrets/PII preflight...")

    gitleaks_bin = shutil.which("gitleaks")
    if not gitleaks_bin:
        err(
            "gitleaks not found on PATH — preflight is fail-closed. Install: brew install gitleaks"
        )
        sys.exit(1)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        report_path = tf.name
    try:
        r = subprocess.run(
            [
                gitleaks_bin,
                "detect",
                "--no-git",
                "--no-banner",
                "-s",
                str(skill_dir),
                "-f",
                "json",
                "-r",
                report_path,
            ],
            capture_output=True,
            text=True,
        )
        try:
            report = json.loads(Path(report_path).read_text() or "[]")
        except (ValueError, OSError):
            report = []
    finally:
        try:
            Path(report_path).unlink()
        except OSError:
            pass

    if not report and r.returncode != 0:
        err(f"gitleaks exited {r.returncode} without a parseable report (fail-closed).")
        tail = r.stderr.strip().splitlines()
        if tail:
            err(f"  {tail[-1]}")
        sys.exit(1)

    sys.path.insert(0, str(SCRIPT_DIR))
    import scan_personal_paths

    pii_findings = scan_personal_paths.scan_skill_dir(skill_dir)

    # Aggregate both scanners so a single blocked run surfaces every problem.
    if report:
        err(f"gitleaks found {len(report)} secret finding(s):")
        for f in report[:20]:
            err(
                f"  {f.get('File', '?')}:{f.get('StartLine', '?')}: {f.get('Description', 'secret')}"
            )
    if pii_findings:
        err(f"personal-path/PII scan found {len(pii_findings)} finding(s):")
        for f in pii_findings[:20]:
            err(f"  {f['path']}:{f['line']}: {f['match']}")

    if report or pii_findings:
        sys.exit(1)

    ok("Secrets/PII preflight passed (gitleaks + personal-path scan)")


def publish_skill(skill_name: str, dry_run: bool, skip_logo: bool, register_note: bool):
    skill_dir = SKILLS_DIR / skill_name

    print()
    print(f"{BOLD}=== Skill Publisher: {skill_name} ==={RESET}")
    if dry_run:
        print(f"{YELLOW}DRY-RUN mode — no changes will be made{RESET}")
    print()

    # ── Step 1: Validate skill directory ─────────────────────────────────────
    info("Validating skill directory...")
    if not skill_dir.is_dir():
        err(f"Skill directory not found: {skill_dir}")
        sys.exit(1)
    ok(f"Skill directory exists: {skill_dir}")

    # ── Step 2: Check required files ─────────────────────────────────────────
    info("Checking required files...")

    abort = False

    if not (skill_dir / "SKILL.md").exists():
        err("SKILL.md is required but missing.")
        abort = True
    else:
        ok("SKILL.md found")

    if not (skill_dir / "README.md").exists():
        err(
            "README.md is required but missing. Run /skill-publisher to generate it first."
        )
        abort = True
    else:
        ok("README.md found")

    if not (skill_dir / "README.zh.md").exists():
        warn("README.zh.md is missing (recommended). Continuing without it.")
    else:
        ok("README.zh.md found")

    if not skip_logo and not (skill_dir / "logo.png").exists():
        warn(
            "logo.png not found. Use --skip-logo to suppress this warning, or run /image-gen to create one."
        )
    elif (skill_dir / "logo.png").exists():
        ok("logo.png found")

    if abort:
        err("Pre-flight checks failed. Aborting.")
        sys.exit(1)

    # ── Step 2.5: Secrets/PII preflight gate (fail-closed, read-only) ─────────
    preflight_secrets_pii(skill_dir)

    # ── Step 3: Initialize git repo ───────────────────────────────────────────
    info("Checking git repository...")

    if not (skill_dir / ".git").exists():
        if dry_run:
            dry(
                f'Would run: git -C "{skill_dir}" init && git -C "{skill_dir}" checkout -b main'
            )
        else:
            run_git(["init", "-q"], cwd=str(skill_dir))
            # Ensure branch is named 'main'
            run_git(["checkout", "-b", "main", "-q"], cwd=str(skill_dir))
            ok("Initialized git repository")
    else:
        ok("Git repository already initialized")

    # ── Step 4: Create .gitignore ─────────────────────────────────────────────
    gitignore_path = skill_dir / ".gitignore"
    info("Checking .gitignore...")
    if not gitignore_path.exists():
        if dry_run:
            dry("Would create .gitignore with standard patterns")
        else:
            gitignore_path.write_text(GITIGNORE_CONTENT)
            ok("Created .gitignore")
    else:
        ok(".gitignore already exists")

    # ── Step 5: Create LICENSE if missing ────────────────────────────────────
    license_path = skill_dir / "LICENSE"
    current_year = datetime.datetime.now().year
    info("Checking LICENSE...")
    if not license_path.exists():
        if dry_run:
            dry("Would create MIT LICENSE")
        else:
            license_path.write_text(MIT_LICENSE_TEMPLATE.format(year=current_year))
            ok("Created MIT LICENSE")
    else:
        ok("LICENSE already exists")

    # ── Step 6: Stage files ───────────────────────────────────────────────────
    info("Staging files...")

    stage_targets = []
    for target in [
        "SKILL.md",
        "README.md",
        "README.zh.md",
        "logo.png",
        ".gitignore",
        "LICENSE",
    ]:
        if (skill_dir / target).exists():
            stage_targets.append(target)
    for d in ["assets", "scripts", "references"]:
        if (skill_dir / d).is_dir():
            stage_targets.append(d)

    if dry_run:
        dry(f"Would stage: {' '.join(stage_targets)}")
    else:
        if stage_targets:
            run_git(["add", "--"] + stage_targets, cwd=str(skill_dir))
            ok(f"Staged: {' '.join(stage_targets)}")

    # ── Step 7: Commit ────────────────────────────────────────────────────────
    info("Preparing commit...")

    r = run_git(["rev-parse", "HEAD"], cwd=str(skill_dir))
    has_commits = r.returncode == 0

    commit_msg = (
        f"Update skill: {skill_name}" if has_commits else f"Publish skill: {skill_name}"
    )

    r = run_git(["diff", "--cached", "--name-only"], cwd=str(skill_dir))
    staged_files = [line for line in r.stdout.splitlines() if line.strip()]
    staged_count = len(staged_files)

    if staged_count == 0:
        warn("Nothing to commit — working tree is clean.")
    else:
        if dry_run:
            dry(f'Would commit: "{commit_msg}"')
            dry("Files to commit:")
            for f in staged_files:
                dry(f"  + {f}")
        else:
            run_git(["commit", "-m", commit_msg, "-q"], cwd=str(skill_dir))
            ok(f'Committed: "{commit_msg}"')

    # ── Step 8: Check / create GitHub repo ───────────────────────────────────
    print()
    info(f"Checking GitHub repo: {GITHUB_ORG}/{skill_name}...")

    r = subprocess.run(
        ["gh", "repo", "view", f"{GITHUB_ORG}/{skill_name}", "--json", "name"],
        capture_output=True,
        text=True,
    )
    repo_exists = r.returncode == 0

    if not repo_exists:
        warn(f"GitHub repo does not exist: {GITHUB_ORG}/{skill_name}")
        create_cmd = (
            f"gh repo create {GITHUB_ORG}/{skill_name} --public "
            f'--source="{skill_dir}" --remote=origin --push'
        )

        if dry_run:
            dry("Would create new repo and push:")
            dry(f"  {create_cmd}")
        else:
            print()
            print(f"{BOLD}Command to execute:{RESET}")
            print(f"  {create_cmd}")
            print()
            try:
                confirm = input("Proceed? [y/N] ").strip()
            except (KeyboardInterrupt, EOFError):
                confirm = ""

            if confirm.lower().startswith("y"):
                r = subprocess.run(
                    [
                        "gh",
                        "repo",
                        "create",
                        f"{GITHUB_ORG}/{skill_name}",
                        "--public",
                        f"--source={skill_dir}",
                        "--remote=origin",
                        "--push",
                    ]
                )
                if r.returncode == 0:
                    ok(
                        f"Repo created and pushed: https://github.com/{GITHUB_ORG}/{skill_name}"
                    )
                else:
                    err("Failed to create repo. Check gh auth status.")
                    sys.exit(1)
            else:
                warn("Skipped repo creation.")
    else:
        ok(f"GitHub repo exists: https://github.com/{GITHUB_ORG}/{skill_name}")

        # Ensure remote is set
        remote_url = f"https://github.com/{GITHUB_ORG}/{skill_name}.git"
        r = run_git(["remote", "get-url", "origin"], cwd=str(skill_dir))
        current_remote = r.stdout.strip() if r.returncode == 0 else ""

        if not current_remote:
            if dry_run:
                dry(f"Would add remote: git remote add origin {remote_url}")
            else:
                run_git(["remote", "add", "origin", remote_url], cwd=str(skill_dir))
                ok("Remote origin added")

        push_cmd = f'git -C "{skill_dir}" push -u origin main'

        if dry_run:
            dry("Would push to existing repo:")
            dry(f"  {push_cmd}")
        else:
            print()
            print(f"{BOLD}Command to execute:{RESET}")
            print(f"  git push -u origin main  (in {skill_dir})")
            print()
            try:
                confirm = input("Proceed? [y/N] ").strip()
            except (KeyboardInterrupt, EOFError):
                confirm = ""

            if confirm.lower().startswith("y"):
                r = run_git(
                    ["push", "-u", "origin", "main"], cwd=str(skill_dir), capture=False
                )
                if r.returncode == 0:
                    ok(f"Pushed to: https://github.com/{GITHUB_ORG}/{skill_name}")
                else:
                    err("Push failed. Check your git remote and credentials.")
                    sys.exit(1)
            else:
                warn("Skipped push.")

    # ── Step 9: Platform registration ────────────────────────────────────────
    # Neither platform can be registered from a script. This step used to GET
    # the DeepWiki page and report "triggered (HTTP 200)" — DeepWiki answers 200
    # for any URL, including repos that do not exist, so all 123 of those
    # successes were fictional and every repo stayed unindexed. It now performs
    # no network calls by default and only prints the manual steps.
    if register_note:
        print()
        info("Platform registration is manual on both platforms:")
        print()
        print(f"{YELLOW}[DeepWiki]{RESET}")
        print(f"  Open   : https://deepwiki.com/{GITHUB_ORG}/{skill_name}")
        print('  Then   : click "Index Repository" (2-10 min). Loading the page does NOT start it.')
        print(
            "  Verify : curl -s "
            f'"https://api.devin.ai/ada/public_repo_indexing_status?repo_name={GITHUB_ORG}%2F{skill_name}"'
        )
        print('           -> {"status":"completed"} indexed, {"status":"unknown"} not indexed')
        print()
        print(f"{YELLOW}[Context7]{RESET}")
        print("  Open   : https://context7.com/add-library (sign in first — the source")
        print("           buttons stay disabled while signed out)")
        print(f"  Submit : https://github.com/{GITHUB_ORG}/{skill_name} on the GitHub tab")
        print("  Note   : one library is processed at a time; submitting a second while")
        print("           the first is parsing is rejected")
        print("  Verify : it appears at https://context7.com/tasklist while processing")

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print(f"{GREEN}{BOLD}=== Done: {skill_name} ==={RESET}")
    if not dry_run:
        print(f"  GitHub : https://github.com/{GITHUB_ORG}/{skill_name}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="publish.py",
        description="Deterministic git + platform registration for skill-publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  publish.py smart-search
  publish.py smart-search --dry-run
  publish.py smart-search --skip-logo --register-note
  publish.py --scan
  publish.py --scan --json
""",
    )

    parser.add_argument(
        "skill_name",
        nargs="?",
        default="",
        help="Name of the skill to publish",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--skip-logo", action="store_true", help="Suppress logo.png warning"
    )
    parser.add_argument(
        "--register-note",
        action="store_true",
        help="Print the manual DeepWiki/Context7 submission steps. Off by "
        "default: neither platform can be registered from a script, and the "
        "old automatic attempt reported success without doing anything.",
    )
    parser.add_argument(
        "--scan", action="store_true", help="Scan all skills publish status"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output scan results as JSON (use with --scan)",
    )

    args = parser.parse_args()

    # ── --scan mode ───────────────────────────────────────────────────────────
    if args.scan:
        scan_script = SCRIPT_DIR / "scan_status.py"
        if not scan_script.exists():
            err(f"scan_status.py not found at: {scan_script}")
            sys.exit(1)
        cmd = [sys.executable, str(scan_script)]
        if args.json:
            cmd.append("--json")
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    # ── Require skill name ────────────────────────────────────────────────────
    if not args.skill_name:
        parser.print_help()
        sys.exit(1)

    publish_skill(
        skill_name=args.skill_name,
        dry_run=args.dry_run,
        skip_logo=args.skip_logo,
        register_note=args.register_note,
    )


if __name__ == "__main__":
    main()
