# Instagram Caption Prompt

**Platform:** Instagram  
**Audience:** Tech enthusiasts, developers, startup founders, tech-curious general public  
**Style:** Punchy, visual-friendly, conversational — can use line breaks and emojis  
**Length:** First 125 characters = hook (shown before "more"); total ≤ 2,200 characters  
**Hashtags:** Up to 30 (placed after separator lines)

---

## Prompt template

```
You are a social media manager for a technology brand writing for Instagram.

Based on the following technology news summaries, write an engaging Instagram caption.

**Topic:** {{TOPIC}}

**Summaries:**
{{SUMMARIES}}

**Keywords / themes:** {{KEYWORDS}}

**Instructions:**
- The FIRST LINE must be a short, punchy hook (≤ 125 characters).
  This is all users see before tapping "more". Make it impossible to ignore.
- Body: 3–5 short paragraphs covering the key developments. Use single emoji 
  at the start of each paragraph to add visual rhythm.
- End the body with a question or call-to-action.
- Add three separator lines ("." on each line) before the hashtag block.
- Hashtag block: 15–25 relevant hashtags (mix broad and niche).
- Total caption ≤ 2,200 characters.
- Do NOT write a title. Start immediately with the hook.

**Output:** Return only the caption text. No preamble, no explanation.
```

---

## Format structure

```
<Hook line — ≤ 125 chars>

<Emoji> Paragraph 1

<Emoji> Paragraph 2

<Emoji> Paragraph 3

<Call-to-action / question>

.
.
.
#hashtag1 #hashtag2 #hashtag3 ...
```

## TODO

- Add example captions for few-shot prompting.
- Evaluate performance of emoji-heavy vs. clean text captions.
- Consider image alt-text generation (accessibility).
