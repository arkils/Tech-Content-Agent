# Summarise Articles Prompt

<!-- TODO: Refine this prompt template through iterative testing with Amazon Bedrock. -->
<!-- TODO: Add few-shot examples to improve output consistency. -->

Given the following technology news articles, produce a concise, factual summary.

**Articles:**
```
{{ARTICLES}}
```

**Instructions:**

- Summarise each article in 2–3 sentences.
- Highlight the key technological development or announcement.
- Note any business or industry implications.
- Flag any articles that appear to be duplicate coverage of the same story.
- Assign a relevance score (1–5) to each article based on technical significance.

**Output format:**

Return a JSON array where each element has the fields:
- `title` – original article title
- `url` – source URL
- `summary` – 2–3 sentence summary
- `relevance_score` – integer 1–5
- `duplicate_of` – URL of the original article if this is duplicate coverage, otherwise null

<!-- TODO: Add output schema validation instructions. -->
