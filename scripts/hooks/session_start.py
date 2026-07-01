#!/usr/bin/env python3
"""
scripts/hooks/session_start.py
==============================
SessionStart hook for tech-news-agent.

Fires at the start of every Copilot agent session and injects the
project's documentation update policy into the agent's system context.

This ensures the agent knows to keep CHANGELOG, roadmap, Q&A skill,
and directory READMEs in sync with every code change — regardless of
what was asked in the prompt.

Called by: .github/hooks/docs-sync.json
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    output = {
        "systemMessage": (
            "=== tech-news-agent documentation policy ===\n\n"
            "This is a Copilot-driven project. Apply these rules for every change made in this session:\n\n"
            "1. CHANGELOG.md — add an entry under [Unreleased] for every meaningful source change.\n"
            "2. docs/roadmap.md — tick off completed milestones with [x] immediately after implementing them.\n"
            "3. Directory READMEs — update the README.md in any directory where files are added or removed.\n"
            "4. Q&A skill — update the relevant file in .github/skills/project-qa/references/ if "
            "project behaviour, architecture, or configuration changes.\n"
            "5. Copilot instruction files — update .github/instructions/*.instructions.md if the "
            "coding pattern or contract for that domain changes.\n\n"
            "The docs-sync hook will remind you which specific files to update after each file write."
        )
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
