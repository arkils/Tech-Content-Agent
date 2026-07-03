# scripts

This directory contains operational, developer helper, and Copilot hook scripts.

## Copilot hooks (`scripts/hooks/`)

These scripts are called automatically by Copilot during agent sessions.
Configured in `.github/hooks/docs-sync.json`.

| Script | Hook event | Purpose |
|--------|-----------|---------|
| `hooks/session_start.py` | `SessionStart` | Injects the project documentation update policy at the start of every session |
| `hooks/docs_sync.py` | `PostToolUse` | After any file write, outputs a `systemMessage` listing which docs must be kept in sync |

### How docs-sync works

`docs_sync.py` reads the tool event JSON from stdin, extracts the modified file path,
matches it against path-pattern rules, and outputs a JSON `systemMessage` telling the
agent which documentation files need updating. Rules cover:

- `agent/publishers/*.py` → `agent/publishers/README.md`, `CHANGELOG.md`, Q&A skill
- `agent/config.py` → configuration Q&A, `docs/deployment.md`, `README.md`
- `agent/tools/*.py` → `agent/tools/README.md`, pipeline diagram, roadmap
- `infrastructure/**` → `docs/deployment.md`, architecture Q&A, roadmap
- `tests/**` → `CHANGELOG.md` test count, `tests/README.md`
- `.github/instructions/` or `.github/skills/` → `CHANGELOG.md`, Copilot YAML validation reminder

## Planned scripts

| Script | Description |
|--------|-------------|
| `bootstrap.sh` | One-command environment setup (venv, pip install, CDK bootstrap) |
| `deploy.sh` | Wrapper around `cdk deploy --all` with pre-flight checks |
| `seed_secrets.sh` | Creates SSM Parameter Store SecureString stubs (no values) in a target account |
| `run_local.py` | Invoke the agent pipeline locally against mocked AWS services |

## TODO

- Implement planned scripts once core agent logic is in place.
- Add Windows-compatible PowerShell equivalents of each script.
