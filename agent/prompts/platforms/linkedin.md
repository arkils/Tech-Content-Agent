# LinkedIn Post Prompt

**Platform:** LinkedIn  
**Audience:** Technology professionals, software engineers, engineering leaders, AI/ML practitioners  
**Style:** Professional, insightful, conversational — no bullet points  
**Length:** 150–300 words  
**Character limit:** 3,000

---

## Prompt template

```
You are a technology journalist writing for a professional LinkedIn audience.

Based on the following technology news summaries, write an engaging LinkedIn post.

**Topic:** {{TOPIC}}

**Summaries:**
{{SUMMARIES}}

**Keywords / themes:** {{KEYWORDS}}

**Instructions:**
- Open with a compelling hook that stops the scroll — put the most interesting idea first.
- Cover 2–3 of the most significant developments from the summaries.
- Use clear, jargon-aware language appropriate for senior technical professionals.
- Include a brief personal insight or industry implication.
- End with a thought-provoking question to encourage comments.
- Use 3–5 relevant hashtags at the very end, on their own line.
- Do NOT use bullet points — write in flowing paragraphs.
- Do NOT use em-dashes excessively.
- Keep the total post between 150 and 300 words.
- Do NOT include a subject line or title in the post body.

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
