#!/usr/bin/env python3
"""
scripts/hooks/docs_sync.py
==========================
PostToolUse hook for tech-news-agent.

Fires after every file-write tool call. Reads the tool event from stdin,
identifies which file was written, and outputs a systemMessage reminding
the agent which documentation files need to be updated in sync.

Rules are defined in SYNC_RULES below — each rule maps a file path pattern
to a list of documentation files that must be kept in sync.

Called by: .github/hooks/docs-sync.json

Exit codes:
    0 — success (always; hook is non-blocking)
"""

from __future__ import annotations

import json
import sys

# ---------------------------------------------------------------------------
# Tools that write files — only these trigger doc-sync reminders.
# ---------------------------------------------------------------------------
FILE_WRITE_TOOLS = {
    "create_file",
    "str_replace_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "edit_notebook_file",
}

# ---------------------------------------------------------------------------
# Sync rules
# Each rule has:
#   patterns      — list of path substrings that activate the rule
#   exclude_suffixes — skip the rule if the path ends with any of these
#   docs          — list of doc files that must be updated in sync
#   note          — optional extra guidance shown in the reminder
# ---------------------------------------------------------------------------
SYNC_RULES: list[dict] = [
    # ── Publisher implementations ──────────────────────────────────────────
    {
        "patterns": ["agent/publishers/"],
        "exclude_suffixes": ["__init__.py", "base.py", "README.md"],
        "docs": [
            "agent/publishers/README.md          — update platform table and status column",
            "CHANGELOG.md                         — add entry under [Unreleased]",
            ".github/skills/project-qa/references/publishers-qa.md — update if behaviour changed",
            "docs/roadmap.md                      — tick off Phase 4 milestones if publish() was implemented",
        ],
    },
    # ── Publisher base contract / registry ────────────────────────────────
    {
        "patterns": ["agent/publishers/__init__.py", "agent/publishers/base.py"],
        "docs": [
            ".github/instructions/publishers.instructions.md — update if the pattern or contract changed",
            ".github/skills/project-qa/references/publishers-qa.md",
            ".github/skills/project-qa/references/architecture-qa.md — ContentPackage / PublishResult section",
            "CHANGELOG.md",
        ],
    },
    # ── Agent config ───────────────────────────────────────────────────────
    {
        "patterns": ["agent/config.py"],
        "docs": [
            ".github/skills/project-qa/references/configuration-qa.md — env vars table",
            "docs/deployment.md                   — if new secrets or env vars were added",
            "README.md                             — publisher configuration table",
            "CHANGELOG.md",
        ],
    },
    # ── Agent tools ────────────────────────────────────────────────────────
    {
        "patterns": ["agent/tools/"],
        "exclude_suffixes": ["README.md", "__init__.py"],
        "docs": [
            "agent/tools/README.md                — update planned/implemented tool table",
            "agent/workflows/news_pipeline.md     — update pipeline diagram",
            ".github/skills/project-qa/references/architecture-qa.md",
            "CHANGELOG.md",
            "docs/roadmap.md                      — tick off Phase 2 milestones",
        ],
    },
    # ── Workflows ──────────────────────────────────────────────────────────
    {
        "patterns": ["agent/workflows/"],
        "exclude_suffixes": ["README.md", "__init__.py"],
        "docs": [
            "agent/workflows/news_pipeline.md     — update stage diagram if pipeline changed",
            ".github/skills/project-qa/references/architecture-qa.md",
            "CHANGELOG.md",
            "docs/roadmap.md                      — tick off Phase 2 milestones",
        ],
    },
    # ── Agent models ───────────────────────────────────────────────────────
    {
        "patterns": ["agent/models/"],
        "exclude_suffixes": ["README.md", "__init__.py"],
        "docs": [
            "agent/models/README.md               — update model table",
            ".github/skills/project-qa/references/architecture-qa.md — data contracts section",
            "CHANGELOG.md",
        ],
    },
    # ── Bedrock prompts ────────────────────────────────────────────────────
    {
        "patterns": ["agent/prompts/"],
        "exclude_suffixes": ["README.md"],
        "docs": [
            "agent/prompts/README.md              — update prompt file table",
            ".github/skills/project-qa/references/architecture-qa.md — Bedrock prompts section",
            "CHANGELOG.md",
        ],
    },
    # ── Infrastructure stacks / constructs ────────────────────────────────
    {
        "patterns": [
            "infrastructure/stacks/",
            "infrastructure/constructs/",
            "infrastructure/app.py",
        ],
        "exclude_suffixes": ["README.md", "__init__.py"],
        "docs": [
            "infrastructure/stacks/README.md      — update stack table",
            "docs/deployment.md                   — if deploy steps or resource names changed",
            ".github/skills/project-qa/references/deployment-qa.md — stack names section",
            ".github/skills/project-qa/references/architecture-qa.md — CDK resources section",
            "CHANGELOG.md",
            "docs/roadmap.md                      — tick off Phase 3 milestones",
        ],
    },
    # ── Tests ──────────────────────────────────────────────────────────────
    {
        "patterns": ["tests/"],
        "exclude_suffixes": ["__init__.py", "conftest.py"],
        "docs": [
            "CHANGELOG.md                         — update test count if it changed",
            "tests/README.md                      — if new test subdirectories were added",
            ".github/skills/project-qa/references/development-qa.md — test structure section",
        ],
    },
    # ── HITL handlers ──────────────────────────────────────────────────────
    {
        "patterns": ["agent/handlers/"],
        "exclude_suffixes": ["__init__.py"],
        "docs": [
            "docs/hitl-plan.md                    — update Phase 4 API route table if routes changed",
            "docs/roadmap.md                      — tick off Phase 5 milestones",
            "CHANGELOG.md",
        ],
    },
    # ── Android app ────────────────────────────────────────────────────────
    {
        "patterns": ["android/"],
        "exclude_suffixes": [".gitignore", ".example", ".xml", ".toml"],
        "docs": [
            "docs/hitl-plan.md                    — update Phase 6 Android structure if files/deps changed",
            "docs/roadmap.md                      — tick off Phase 5 Android milestones",
            "CHANGELOG.md",
        ],
        "note": "Ensure local.properties and google-services.json remain excluded from git.",
    },
    # ── HITL plan doc ──────────────────────────────────────────────────────
    {
        "patterns": ["docs/hitl-plan.md"],
        "docs": [
            "docs/roadmap.md                      — keep Phase 5 items in sync with hitl-plan.md",
            ".github/instructions/android.instructions.md — update key reference pointers if sections renamed",
        ],
    },
    # ── Copilot customisation files ────────────────────────────────────────
    {
        "patterns": [
            ".github/instructions/",
            ".github/skills/",
            ".github/copilot-instructions.md",
        ],
        "exclude_suffixes": [],
        "docs": [
            "CHANGELOG.md                         — if this was a meaningful knowledge update",
            "docs/roadmap.md                      — if this completes a documentation milestone",
        ],
        "note": "Verify that frontmatter YAML is valid (no unescaped colons, no tab characters).",
    },
    # ── GitHub Actions workflows ───────────────────────────────────────────
    {
        "patterns": [".github/workflows/"],
        "docs": [
            "docs/deployment.md                   — if CI/CD steps changed",
            ".github/skills/project-qa/references/deployment-qa.md — OIDC / deploy section",
            "CHANGELOG.md",
        ],
    },
]


def get_file_path(event: dict) -> str | None:
    """Extract the written file path from a PostToolUse event payload."""
    tool_input = (
        event.get("toolInput")
        or event.get("input")
        or event.get("tool_input")
        or {}
    )
    for key in ("filePath", "file_path", "path", "target_file"):
        if key in tool_input:
            return str(tool_input[key])
    return None


def normalise(path: str) -> str:
    """Normalise path separators for consistent pattern matching."""
    return path.replace("\\", "/")


def find_rule(file_path: str) -> dict | None:
    """Return the first SYNC_RULES entry whose pattern matches the path."""
    norm = normalise(file_path)
    for rule in SYNC_RULES:
        excludes = rule.get("exclude_suffixes", [])
        if any(norm.endswith(ex) for ex in excludes):
            continue
        if any(pattern in norm for pattern in rule["patterns"]):
            return rule
    return None


def build_message(file_path: str, rule: dict) -> str:
    docs_list = "\n".join(f"  • {d}" for d in rule["docs"])
    note_line = f"\n  ⚠ Note: {rule['note']}" if rule.get("note") else ""
    return (
        f"[docs-sync] `{file_path}` was modified.\n\n"
        f"Update these files to keep documentation in sync:\n"
        f"{docs_list}"
        f"{note_line}"
    )


def main() -> None:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    # Only fire on file-write tools
    tool_name = event.get("toolName") or event.get("tool") or ""
    if tool_name not in FILE_WRITE_TOOLS:
        sys.exit(0)

    file_path = get_file_path(event)
    if not file_path:
        sys.exit(0)

    rule = find_rule(file_path)
    if not rule:
        sys.exit(0)

    output = {"systemMessage": build_message(file_path, rule)}
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
