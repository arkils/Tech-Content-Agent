---
applyTo: "agent/publishers/**"
---

# Publisher Implementation Instructions

When implementing or extending a publisher in `agent/publishers/`:

## Required structure

Every publisher module must follow this exact pattern:

```python
"""
agent/publishers/<platform>.py
================================
<Platform> content publisher.

<One paragraph explaining the platform, API used, and credential requirements.>

Expected SSM Parameter Store JSON structure::

    {
        "key_name": "<value-description>"
    }

TODO:
    - Implement _get_credentials() using boto3 SSM Parameter Store.
    - Implement publish() using the <Platform> API.
    - Add token refresh if applicable.
"""

from __future__ import annotations

import logging

from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

logger = logging.getLogger(__name__)


class <Platform>Publisher(BasePublisher):
    platform_name = "<platform_key>"

    def format_content(self, package: ContentPackage) -> str:
        """
        Format ContentPackage for <Platform>.
        TODO: Call Bedrock with agent/prompts/platforms/<platform>.md
        """
        ...

    def publish(self, content: str) -> PublishResult:
        """
        Deliver content to <Platform>.
        TODO: Retrieve credentials from AWS SSM Parameter Store.
        """
        raise NotImplementedError(...)
```

## Credential retrieval pattern

```python
def _get_credentials(self, ssm_client) -> dict:
    """Fetch platform credentials from AWS SSM Parameter Store."""
    import json
    response = ssm_client.get_parameter(
        Name=AgentConfig.<PLATFORM>_PARAM_PATH, WithDecryption=True
    )
    return json.loads(response["Parameter"]["Value"])
```

- **Never** cache credentials across invocations — always fetch fresh.
- **Never** log credential values — log only success/failure.

## PublishResult contract

Always return a `PublishResult`:

```python
# Success
return PublishResult(platform=self.platform_name, success=True, post_id="...", url="...")

# Failure
return PublishResult(platform=self.platform_name, success=False, error=str(exc))
```

## Registration

After creating the module, add to `PUBLISHER_REGISTRY` in `agent/publishers/__init__.py`:

```python
from agent.publishers.<platform> import <Platform>Publisher

PUBLISHER_REGISTRY: dict[str, type[BasePublisher]] = {
    ...,
    "<platform_key>": <Platform>Publisher,
}
```

And add the parameter path to `AgentConfig` in `agent/config.py`:

```python
<PLATFORM>_PARAM_PATH: str = "/tech-news-agent/<platform>"
```

## Required files per new platform

1. `agent/publishers/<platform>.py` — publisher implementation
2. `agent/prompts/platforms/<platform>.md` — Bedrock prompt template
3. `tests/publishers/test_<platform>.py` — unit tests
4. Entry in `agent/publishers/README.md` platform table
5. Parameter path in `agent/config.py`
