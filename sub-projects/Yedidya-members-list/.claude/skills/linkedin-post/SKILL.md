---
name: linkedin-post
description: Write or refine a LinkedIn post. Use when the user asks to write, draft, create, edit, improve, or iterate on a LinkedIn post, or mentions LinkedIn content.
---

# LinkedIn Post

Write or refine a LinkedIn post from an idea or existing draft. Output a copy-paste-ready post.

## Before You Start

1. **Confirm language.** The default is Hebrew (with English terms where natural for an Israeli audience). If the user hasn't specified, ask: "עברית או אנגלית?"
2. **Read the input.** Either a clear idea for a new post, or an existing draft to refine. If the idea is vague, ask one clarifying question before writing.
3. **Read core files** — `core/tone-of-voice.md`, `core/user-identity.md`, `core/project-brief.md` — so the post sounds like the user, not like generic AI.
4. **Find the voice fingerprint.** Before writing, note 2-3 specific things about how this person talks — not just their profession, but their personality. Are they blunt? Sarcastic? Analytical? Do they use metaphors or data? This shapes sentence structure, not just word choice.
5. **Identify the post type** (see Post Types below). Different types need different structures — a story post and an opinion post shouldn't read the same way.
6. **If writing in Hebrew**, use the `/writing-hebrew` skill. Run the post through it before delivering.

## Post Types

Not every post is a story. Identify the type before writing — it determines the structure.

**Story / Lesson** — Something happened, you learned from it. Structure: scene → tension → turn → insight. The story does the work; don't explain the moral if the story already delivered it.

**Opinion / Hot Take** — You believe something others might not. Structure: state the position early (first 2-3 lines), then make the case. One strong argument beats three weak ones. End with the implication, not a summary.

**Educational / How-To** — You know something useful. Structure: name the problem, give the solution. Be specific — "here's exactly what I did" beats "here are 5 tips." Keep it to one technique per post, not a listicle.

**Observation** — You noticed something others haven't articulated. Structure: describe what you see, then say why it matters. The observation IS the hook — lead with it.

**Milestone / Announcement** — Something happened in your work. Structure: the news in 1-2 lines, then the human story behind it. "We raised $X" is boring. Why it matters to you isn't.

The type shapes the structure, but the voice stays constant. A story post and an opinion post should both sound like the same person.

## The Post — What Makes It Good

### One idea. One post.

The fundamental mistake is cramming multiple tips, stories, or angles into one post. Pick one thing. If you have five points, that's five posts.

### The hook (lines 1-2)

These lines appear before "See more." They must stop the scroll.

A good hook does one of these things:

| Pattern | Tired version | Better version |
|---------|--------------|----------------|
| Contradiction | "AI will replace us all" | "I automated my job. Then I got promoted." |
| Specificity | "I learned something about leadership" | "My best manager never gave me feedback" |
| Tension | "Exciting news!" | "I almost quit last Tuesday" |
| Observation | "The market is changing" | "Every founder I talk to is lying about the same thing" |
| Direct address | "5 tips for better..." | "You're writing LinkedIn posts wrong" |

These aren't templates to copy — they're patterns to riff on. The common thread: something unexpected, specific, or unresolved in the first line. The reader needs a reason to click "See more" that isn't just curiosity-bait.

**What kills a hook:** starting with context ("In today's fast-paced..."), announcements ("I'm excited to share..."), or throat-clearing ("I've been thinking a lot about..."). Start with the thing, not the setup to the thing.

### The body

**Visual rhythm is everything.** When you squint at a great LinkedIn post, it looks something like this:

```
████████████                          ← short

██████████████████████████████████████████████████████████████████
██████████████████████████████████████████████████████        ← long

███████████████████                   ← medium

██████████████████████████████████████████████████████
                                                              ← long

██████████████                        ← short


██████████████████████████████████████████████████████████████████
██████████████████████████████████████████████████████████████████
█████████████████████████████████████████████████      ← long block

████████████████████████████████████         ← medium

██████████████████████████████████████████████████████████████████
████████████████████████████████████████████████████   ← long

██████                                ← short
```

This isn't a template to match literally — it's a compass. The point is: blocks should vary in size. Short lines, then a longer thought that gives context and keeps people reading because it flows naturally, then short again. The rhythm is what makes people keep scrolling.

The test: squint at the post until you can barely read the words. If all the blocks look the same size — rewrite. If they have variety — you're good.

**When telling a story:**

Stories are the highest-engagement format on LinkedIn, but AI tends to flatten them into lesson-delivery vehicles. A good story has:

- **A scene.** Not "I had a meeting once" — ground it. When, where, who. One sentence is enough: "Last Thursday, 11pm, I'm rewriting the pitch deck for the third time."
- **Tension.** Something at stake, uncertain, or uncomfortable. Without tension there's no reason to keep reading.
- **A turn.** The moment something shifted — a realization, a surprise, a decision. This is the post's center of gravity.
- **An insight that earns itself.** The reader should feel it coming from the story, not from you explaining it. If you need a paragraph after the story to explain what it meant — the story didn't land.

The biggest mistake: writing the story as setup for a lesson. The story IS the content. The lesson, if there is one, should feel like an afterthought the reader arrives at themselves.

**Formatting rules:**
- Short paragraphs (1-3 sentences)
- Line breaks between thoughts
- Selective bold for emphasis (sparingly)
- Maximum one emoji in the entire post (zero is fine)
- Use "I" not "we" for personal posts

### The close

End purposefully. Three options — vary them, don't default to the same one every time:
- **A question** that could only follow this specific story. Not a generic "what do you think?" — a question that wouldn't make sense under any other post.
- **A lingering reflection** the reader sits with. Half-open. No neat bow.
- **Let the story end itself.** If the narrative already delivered the insight, stop. Don't restate it.

**Trust the story.** If the reader already got the point from what happened, a lesson paragraph dilutes it. The best posts end closer to the moment, not after an explanation of what the moment meant.

Never: "Comment YES if you agree," sharing demands, engagement farming, quotable redefinitions ("X isn't Y, it's Z"), or any close that sounds like it belongs on a screenshot.

### Length

Sweet spot: 150-300 words. Maximum 3,000 characters. Generous whitespace — dense text kills engagement.

## Voice

The post must sound like the user. Not like "LinkedIn content." Not like AI.

- **Authentic over performative.** Real experiences with reflection, not manufactured vulnerability.
- **Dugri (direct).** Israeli audiences value directness. Skip the corporate polish.
- **Personal stories over corporate content.** First person. Specific. A moment, not a thesis.
- **Failures and lessons land hard.** Israeli LinkedIn rewards honesty about what didn't work.
- **No slop.** If a sentence could appear in any LinkedIn post by anyone — delete it.

## When Refining an Existing Draft

When the user provides a draft to improve:

1. **Don't rewrite from scratch** unless the draft is fundamentally broken. Preserve the user's voice and intent.
2. **Apply the rhythm test first.** Squint at the draft — are the blocks varied? Fix the visual structure.
3. **Check the hook.** Is it scroll-stopping or generic? This is the highest-leverage fix.
4. **Trim.** Most drafts are too long. Cut filler, tighten phrasing, remove redundant points.
5. **If Hebrew**, run through `/writing-hebrew` to catch AI tells.
6. **Show what you changed and why** — briefly, so the user learns.

## Anti-Patterns

**Content:** humble-brags, recycled viral formats, tragedy exploitation, uncredited frameworks, corporate announcements dressed as personal stories.

**Format:** every sentence on its own line (staccato), excessive emoji, ALL CAPS emphasis.

**Tone:** performed vulnerability, motivational poster language, "I'm SO excited to share this!", anything that sounds like a translated TED talk.

**Closes:** ending with a polished redefinition or quotable reframe in any form. All of these are the same crutch:
- "X isn't Y, it's Z"
- "X doesn't mean Y"
- "X without Y is just Z"
- Any sentence that redefines a concept in a way that sounds quotable

If the last line sounds like it belongs on a screenshot or a motivational poster, rewrite it.

## Output

Save to `output/linkedin-post-[short-topic]-[YYYY-MM-DD].md` in this format:

```
[The full post text, ready to copy-paste into LinkedIn]
```

No markdown formatting that doesn't work on LinkedIn. No headers. Just the text as it should appear on the platform.

## Quality Checklist (internal — don't show to user)

Before delivering, verify:
- [ ] Hook — would this stop your scroll?
- [ ] One idea, not three?
- [ ] Visual rhythm — blocks vary in size?
- [ ] Sounds like the user, not like AI?
- [ ] No filler, no slop, no corporate speak?
- [ ] If Hebrew — passed through `/writing-hebrew`?
- [ ] Post type — does the structure match the type? (story ≠ opinion ≠ educational)
- [ ] **Close audit (mandatory).** Read the last 3 lines of the post. For each line, ask:
  - Does this line restate the story's insight? → Delete it. The story already landed.
  - Does this line work as a standalone quote or screenshot? → Delete it. It's a quotable reframe in disguise.
  - Is this a question that could appear under a different post on a different topic? → Delete it. Either make it specific to this story or end without a question.
  - After deleting, does the post still end well? If the last narrative beat is strong, it probably does.
- [ ] Length: 150-300 words?
