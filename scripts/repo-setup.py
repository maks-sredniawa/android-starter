#!/usr/bin/env python3
"""The GitHub-side setup a repository generated from this template still owes.

    python3 scripts/repo-setup.py --dry-run   # what it would change, and what is already right
    python3 scripts/repo-setup.py             # do it

**None of this is inherited.** GitHub's template mechanism copies files and nothing else: no
rulesets, no branch protection, no secrets, no merge-strategy preference. A repo created from
the template starts with `main` wide open and every one of these undone, and the build stays
green the whole time — the first symptom is a release PR that never appears, which reads like a
broken template rather than an unconfigured repository.

That is why this script exists rather than a paragraph asking you to remember the UI journeys.
It is idempotent: run it again after any manual change and it reports what is already correct
instead of fighting you.

What it cannot do is mint the PAT. GitHub has no API for creating a personal access token, so
`RELEASE_PLEASE_TOKEN` stays a manual step; the script tells you whether it is set and stops
short of pretending otherwise. Same for the Play secrets, which you set when the first upload is
actually near.

Needs `gh`, authenticated (`gh auth status`), run from inside the repository.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"

RULESET_NAME = "main: require CI"

# The status checks the ruleset requires, by the `name:` CI gives each job. Both are deliberate
# choices rather than every job in the file: `Build, unit tests, lint` is the cheap gate, and
# `Instrumented tests` is the *aggregate* job (`instrumented-gate`), not the matrix legs. The
# aggregate runs with `always()` so a failed leg still reports — a skipped required check never
# reports at all, and a PR waiting on one hangs forever.
REQUIRED_CHECKS = ["Build, unit tests, lint", "Instrumented tests"]

# Secrets, and whether the repo is unusable without them. RELEASE_PLEASE_TOKEN is the only one
# needed before the first release; the rest are wanted at the first Play upload and not before.
SECRETS = [
    ("RELEASE_PLEASE_TOKEN", True),
    ("UPLOAD_KEYSTORE_BASE64", False),
    ("UPLOAD_STORE_PASSWORD", False),
    ("UPLOAD_KEY_ALIAS", False),
    ("UPLOAD_KEY_PASSWORD", False),
    ("PLAY_SERVICE_ACCOUNT_JSON", False),
]


def gh(*args: str, check: bool = True) -> str:
    """Run `gh` and hand back stdout. Failures print gh's own stderr, which is usually the
    actionable message (a 403 naming the missing scope beats anything this script could invent).
    """
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, cwd=ROOT
    )
    if check and result.returncode != 0:
        print(f"repo-setup: `gh {' '.join(args)}` failed:\n{result.stderr.strip()}", file=sys.stderr)
        raise SystemExit(1)
    return result.stdout.strip()


def api(path: str, method: str = "GET", body: dict | None = None, check: bool = True) -> str | None:
    """Call the GitHub API. Returns stdout, or None when the call failed and `check` is False.

    The None matters: `gh api` writes the *error body* to stdout on a 404, so a probe that only
    asks "was stdout empty?" reads `{"message": "Not Found"}` as a successful answer. Every
    optional lookup here has to go by the exit code instead.
    """
    args = ["gh", "api", "-X", method, path]
    stdin = json.dumps(body) if body is not None else None
    if body is not None:
        args += ["--input", "-"]
    result = subprocess.run(args, input=stdin, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        if check:
            print(f"repo-setup: {method} {path} failed:\n{result.stderr.strip()}", file=sys.stderr)
            raise SystemExit(1)
        return None
    return result.stdout.strip()


def check_names_exist() -> None:
    """Refuse to require a status check that CI does not publish.

    A required check that never reports is worse than no rule: every PR sits at "Expected —
    waiting for status to be reported" with no way forward but deleting the ruleset. So the job
    names are verified against ci.yml before the ruleset is created, and a rename here is a loud
    failure rather than a repository nobody can merge into.
    """
    if not CI_WORKFLOW.exists():
        print(f"repo-setup: no {CI_WORKFLOW.relative_to(ROOT)}", file=sys.stderr)
        raise SystemExit(2)
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    names = set(re.findall(r"^\s*name:\s*(.+?)\s*$", text, re.MULTILINE))
    missing = [c for c in REQUIRED_CHECKS if c not in names]
    if missing:
        print(
            "repo-setup: these checks are not job names in ci.yml, so requiring them would "
            f"hang every PR: {missing}\nEdit REQUIRED_CHECKS to match the workflow.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def ensure_ruleset(repo: str, dry_run: bool) -> None:
    existing = json.loads(api(f"repos/{repo}/rulesets") or "[]")  # 404 is fatal here, by design
    if any(r["name"] == RULESET_NAME for r in existing):
        print(f"  ruleset {RULESET_NAME!r} already exists — left alone")
        return
    if dry_run:
        print(f"  would create ruleset {RULESET_NAME!r} requiring {REQUIRED_CHECKS}")
        return
    api(
        f"repos/{repo}/rulesets",
        "POST",
        {
            "name": RULESET_NAME,
            "target": "branch",
            "enforcement": "active",
            # Empty on purpose. A bypass actor is a hole in the one rule that stops an
            # untested commit reaching main, and the release PR must pass CI like any other.
            "bypass_actors": [],
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": False,
                        "do_not_enforce_on_create": False,
                        "required_status_checks": [{"context": c} for c in REQUIRED_CHECKS],
                    },
                },
                {"type": "deletion"},
                {"type": "non_fast_forward"},
            ],
        },
    )
    print(f"  created ruleset {RULESET_NAME!r} requiring {', '.join(REQUIRED_CHECKS)}")


def ensure_merge_strategy(repo: str, dry_run: bool) -> None:
    """Rebase only. This is load-bearing for the changelog, not taste — GitHub writes the PR
    title into a merge commit's body, so a `feat:` PR whose branch carries that same subject is
    parsed twice and the release notes list the feature twice. See docs/RELEASING.md.
    """
    current = json.loads(api(f"repos/{repo}"))
    wanted = {"allow_merge_commit": False, "allow_squash_merge": False, "allow_rebase_merge": True}
    drift = {k: v for k, v in wanted.items() if current.get(k) != v}
    if not drift:
        print("  merge strategy already rebase-only")
        return
    if dry_run:
        print(f"  would set {drift}")
        return
    api(f"repos/{repo}", "PATCH", wanted)
    print("  merge strategy set to rebase-only")


def report_secrets(repo: str) -> list[str]:
    have = {line.split("\t")[0] for line in gh("secret", "list", "--repo", repo).splitlines() if line}
    blocking = []
    for name, required in SECRETS:
        if name in have:
            print(f"  {name}: set")
        elif required:
            print(f"  {name}: MISSING — no release PR will ever be opened without it")
            blocking.append(name)
        else:
            print(f"  {name}: not set (needed at the first Play upload, not before)")
    return blocking


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report, change nothing")
    args = parser.parse_args()

    check_names_exist()
    repo = json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]
    print(f"repo: {repo}{'  (dry run)' if args.dry_run else ''}\n")

    print("branch protection")
    ensure_ruleset(repo, args.dry_run)
    print("merge strategy")
    ensure_merge_strategy(repo, args.dry_run)
    print("secrets")
    blocking = report_secrets(repo)

    if blocking:
        print(
            "\nStill owed, and not scriptable: GitHub has no API for minting a personal access\n"
            "token, so create it by hand and set it:\n"
            "  https://github.com/settings/personal-access-tokens/new\n"
            "  fine-grained, this repository only, Contents: read+write, Pull requests: read+write\n"
            f"  gh secret set RELEASE_PLEASE_TOKEN --repo {repo}"
        )
        return 1
    print("\nAll set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
