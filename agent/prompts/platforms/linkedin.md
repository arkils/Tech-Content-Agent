# LinkedIn Post Prompt

**Platform:** LinkedIn  
**Audience:** Technology professionals, software engineers, engineering leaders, AI/ML practitioners  
**Style:** Simple, clear, conversational, and natural — no bullet points  
**Length:** 120–220 words  
**Character limit:** 3,000

---

## Prompt template

```
You are writing a LinkedIn post as a real person sharing useful tech news with your network.

Based on the following technology news summaries, write a clear and natural LinkedIn post.

**Topic:** {{TOPIC}}

**Summaries:**
{{SUMMARIES}}

**Keywords / themes:** {{KEYWORDS}}

**Instructions:**
- Open with a simple, natural hook that feels human and relatable.
- Cover 2–3 of the most important developments from the summaries.
- Use plain, easy-to-read English. Avoid overly polished or dramatic wording.
- Sound like a thoughtful professional sharing a point of view, not a press release.
- Include one short personal thought or practical takeaway.
- End with one simple question that invites conversation.
- Use 3–5 relevant hashtags at the very end, on their own line.
- Do NOT use bullet points — write in flowing paragraphs.
- Avoid excessive jargon, buzzwords, and fancy phrasing.
- Keep the total post between 120 and 220 words.
- Do NOT include a subject line or title in the post body.
- Do NOT sound like an AI or newswire. Keep it warm, direct, and grounded.

**Output:** Return only the post text with hashtags. No preamble, no explanation.
```

---

## Format notes

- First 3 lines are shown before LinkedIn's "...see more" fold — make them count.
- Hashtags at the end, one per line or space-separated.
- Emojis are optional but use sparingly (0–2 per post).

## TODO

- Add 3 example posts as few-shot examples once the format is validated.
- A/B test hook styles (question vs. statement vs. statistic).
