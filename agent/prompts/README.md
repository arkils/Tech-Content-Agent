# agent/prompts

This directory contains prompt templates used by Amazon Bedrock.

| File | Purpose |
|------|---------|
| `system.md` | System-level instruction given to the model at the start of every session |
| `summarize.md` | Prompt template for summarising a batch of news articles |
| `linkedin.md` | Prompt template for generating a LinkedIn post from summaries |

## Guidelines

- Keep prompts version-controlled — changes here directly affect agent behaviour.
- Use `{{PLACEHOLDER}}` syntax for dynamic values injected at runtime.
- Review prompt changes in pull requests like any other code change.

## TODO

- Add prompt versioning strategy.
- Add evaluation criteria for each prompt.
