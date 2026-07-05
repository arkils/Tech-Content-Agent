"""
scripts/run_local.py
====================
Run the tech-news-agent pipeline locally against real AWS services.

Prerequisites
-------------
- AWS credentials configured in ~/.aws/credentials (or via AWS_PROFILE env var).
- SSM Parameter Store parameters present in your account:
    /tech-news-agent/linkedin   — {"access_token": "...", "author_urn": "..."}
    /tech-news-agent/openai     — {"api_key": "sk-..."}   (if using OpenAI)
- DynamoDB tables deployed (run `cdk deploy TechNewsAgentStorage` first).
- A .env.local file copied from .env.example and filled in.

Usage
-----
    python scripts/run_local.py               # uses .env.local if present
    python scripts/run_local.py --dry-run     # forces ENABLE_POSTING=false
    python scripts/run_local.py --force-new   # forces FORCE_NO_NEW_ARTICLES=true
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure project root is on sys.path so `agent.*` imports resolve.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# .env.local loader (no external dependencies required)
# ---------------------------------------------------------------------------

def _load_env_file(path: Path) -> None:
    """
    Load KEY=VALUE pairs from a .env file into os.environ.

    - Lines starting with # are treated as comments.
    - Empty lines are skipped.
    - Values are NOT overridden if the variable is already set in the shell.
    - Inline comments (after a #) are stripped.
    - Values wrapped in single or double quotes are unquoted.
    """
    if not path.exists():
        return

    print(f"Loading environment from {path}")
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            print(f"  [WARN] {path.name}:{lineno}: skipping malformed line: {raw_line!r}")
            continue

        key, _, raw_value = line.partition("=")
        key = key.strip()
        # Strip inline comment
        value = raw_value.split("#")[0].strip()
        # Unquote
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]

        if key and key not in os.environ:
            os.environ[key] = value


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _get_runtime_config() -> object:
    """Return an AgentConfig instance after env variables have been applied."""
    from agent.config import AgentConfig  # noqa: PLC0415

    return AgentConfig()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the tech-news-agent pipeline locally.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force ENABLE_POSTING=false — generate posts but do not publish.",
    )
    parser.add_argument(
        "--force-new",
        action="store_true",
        help="Force FORCE_NO_NEW_ARTICLES=true — bypass deduplication.",
    )
    parser.add_argument(
        "--env-file",
        default=str(_PROJECT_ROOT / ".env.local"),
        help="Path to the .env file to load (default: .env.local in project root).",
    )
    args = parser.parse_args()

    # Load env file before anything imports AgentConfig
    _load_env_file(Path(args.env_file))

    # CLI flag overrides
    if args.dry_run:
        os.environ["ENABLE_POSTING"] = "false"
        print("--dry-run: ENABLE_POSTING forced to false")
    if args.force_new:
        os.environ["FORCE_NO_NEW_ARTICLES"] = "true"
        print("--force-new: FORCE_NO_NEW_ARTICLES forced to true")

    # Late import — AgentConfig reads env vars at class definition time
    config = _get_runtime_config()
    from agent.main import handler  # noqa: PLC0415

    # Configure logging for local console output
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n" + "=" * 60)
    print("tech-news-agent — local run")
    print("=" * 60)
    print(f"  AWS region      : {config.aws_region}")
    print(f"  LLM provider    : {config.llm_provider}")
    print(f"  Bedrock model   : {config.bedrock_model_id}")
    print(f"  OpenAI model    : {config.openai_model_id}")
    print(f"  Publishers      : {', '.join(config.enabled_publishers)}")
    print(f"  Enable posting  : {config.enable_posting}")
    print(f"  Articles table  : {config.dynamodb_table_name}")
    print(f"  Posts table     : {config.posts_table_name}")
    print(f"  Force new arts  : {config.force_no_new_articles}")
    print("=" * 60 + "\n")

    result = handler(event={}, context=None)  # type: ignore[arg-type]

    print("\n" + "=" * 60)
    print("Pipeline result")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60 + "\n")

    if result.get("status") == "skipped":
        print(f"Pipeline skipped: {result.get('skip_reason')}")
        print("Tip: set FORCE_NO_NEW_ARTICLES=true (or use --force-new) to bypass deduplication.")
    elif result.get("publishers_succeeded", 0) == result.get("publishers_total", 0):
        print("All publishers completed successfully.")
    else:
        failed = result.get("publishers_total", 0) - result.get("publishers_succeeded", 0)
        print(f"{failed} publisher(s) failed — check the logs above for details.")


if __name__ == "__main__":
    main()
