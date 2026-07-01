# Blog Post Prompt

**Platform:** Blog / Markdown (GitHub Pages, Hugo, Docusaurus, Hashnode, Dev.to)  
**Audience:** Technical readers who want depth — developers, architects, tech leads  
**Style:** Informative, analytical, well-structured — authoritative but approachable  
**Length:** 600–1,200 words  
**Format:** Markdown with front-matter

---

## Prompt template

```
You are a senior technology writer producing a blog post for a technical audience.

Based on the following technology news summaries, write a well-structured blog post in Markdown.

**Topic:** {{TOPIC}}

**Summaries:**
{{SUMMARIES}}

**Keywords / themes:** {{KEYWORDS}}

**Source articles:**
{{SOURCE_LINKS}}

**Instructions:**
- Write in clear, precise English suitable for senior software engineers and architects.
- Structure the post with the following sections:
  1. **Introduction** — set the scene, state the key theme (2–3 sentences).
  2. **What happened** — factual summary of the major developments.
  3. **Why it matters** — analysis and industry implications.
  4. **Key takeaways** — 3–5 concise bullet points.
  5. **Sources** — properly formatted Markdown links.
- Use Markdown headings (##, ###), bullet lists, and bold emphasis appropriately.
- Do NOT use H1 (# heading) — the front-matter title handles that.
- Cite sources inline where specific claims are made: [Source Name](URL).
- Do NOT fabricate statistics, quotes, or features not present in the summaries.
- Target 600–1,000 words for the body (excluding front-matter and sources).
- Tone: professional and analytical. Avoid sensationalism.

**Output:** Return only the Markdown body (no front-matter). No preamble, no explanation.
```

---

## Front-matter

The `BlogPublisher` automatically prepends YAML front-matter:

```yaml
---
title: "{{TOPIC}}"
date: "{{ISO_DATE}}"
tags: [{{KEYWORDS}}]
draft: false
---
```

## TODO

- Add few-shot example posts.
- Add support for generating a Twitter/X thread from the same content.
- Consider generating an SEO meta-description field.
- Add reading-time estimate to front-matter.
