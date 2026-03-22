---
name: writing-hebrew
description: Use when writing Hebrew or editing Hebrew text — any format, any register. Detects and fixes patterns that make Hebrew sound AI-generated. Triggers on Hebrew content creation, כתוב בעברית, תשפר את העברית, Hebrew copy, or any task producing Hebrew output.
---

# Writing Hebrew

A pattern-based linter for Hebrew text. Detects AI tells, fixes them, checks the result.

## How to Use

1. Write (or receive) Hebrew text
2. Run through the **AI Tells** — fix every match
3. Apply the **Writing Principles**
4. Run the **Quality Check**
5. If 3+ issues found, rewrite from scratch — don't patch

---

## AI Tells

Patterns that signal "an LLM wrote this." Each has a detection rule and a fix.

### T1 — Em Dashes

Hebrew doesn't use em dashes (—). They're English punctuation that AI drops into Hebrew constantly.

| Tell | Fix |
|------|-----|
| הפתרון — שמבוסס על טכנולוגיה — עובד | הפתרון מבוסס על טכנולוגיה, והוא עובד |
| המטרה — להגיע ליותר לקוחות | המטרה: להגיע ליותר לקוחות |

Restructure with comma, colon, or period. If you must dash, use en-dash (–).

### T2 — Parenthetical English

Translating a Hebrew term into English in parentheses. Native Hebrew writers never do this.

| Tell | Fix |
|------|-----|
| אסטרטגיה עסקית (Business Strategy) | אסטרטגיה עסקית |
| חוויית משתמש (User Experience) | חוויית משתמש |

Delete the English. The reader either knows the term or doesn't need it.

### T3 — Gender Mismatch

Two problems AI gets wrong:

**Audience address:** AI defaults to אתה (masculine singular). Real Hebrew matches the audience.

| Tell | Fix |
|------|-----|
| עליך להירשם | הירשמו / תירשמו |
| כעת אתה יכול | עכשיו אפשר |
| אם תרצה לדעת יותר | אם מעניין אתכם |

Use plural for groups. Use gender-neutral phrasing (אפשר, שווה, כדאי) when addressing mixed audiences.

**Narrator voice:** When writing as a specific person, every verb, adjective, and participle in first person must match their gender. AI often defaults to masculine forms even for feminine narrators.

| Tell | Fix |
|------|-----|
| אני מכוון (for a woman) | אני מכוונת / בכוונה |
| הייתי בטוח (for a woman) | הייתי בטוחה |
| אני חושב ש (for a woman) | אני חושבת ש |

If the person's gender is known, scan every first-person form. One mismatch breaks immersion for a native reader.

**Important:** Avoiding gendered forms entirely (by only using conjugations that happen to be gender-neutral) is itself an AI tell. When the narrator's gender is known, include at least 1-2 clearly gendered first-person forms — adjectives, participles, or other forms that signal gender. A woman writing naturally will say "הייתי בטוחה" or "הרגשתי מתוסכלת", not only "הייתי" and "הרגשתי".

### T4 — Filler Phrases

AI scatters these like confetti. Once per page — maybe. Three per paragraph — AI.

**Detect:** חשוב לציין, ראוי להדגיש, יש לציין, בהקשר הזה, מעניין לראות ש, ניתן לראות ש, יש לשים לב ש

**Fix:** Delete the filler, say the thing directly.
"חשוב לציין שהמחירים עלו" → "המחירים עלו"

### T5 — Compulsive Closers

AI wraps up everything, even two-paragraph texts.

**Detect:** לסיכום, בשורה התחתונה, ניתן לסכם ולומר, באופן כללי, Overall

**Fix:** If the reader remembers what you just said — stop writing. Don't summarize.

### T6 — Automatic Triads

AI defaults to listing in threes — three adjectives, three benefits, three anything. Triads aren't always wrong, but when every list has exactly three items, it's a pattern, not a choice.

| Tell | Fix |
|------|-----|
| חדשני, יצירתי ומקצועי | Pick one — unless all three genuinely matter |
| מהיר, פשוט ויעיל | מהיר. (is "simple" adding anything? is "efficient" just restating "fast"?) |

Use three when three things need saying. Use one when one is enough.

### T7 — Smooth Text

Human text has rhythm — short punches next to long thoughts, asides, half-finished ideas. AI text is uniformly smooth, every sentence about the same length, same structure, same pace.

| Tell | Fix |
|------|-----|
| המערכת עובדת היטב. היא מספקת תוצאות טובות. המשתמשים מרוצים ממנה. | המערכת עובדת. תוצאות? טובות. המשתמשים? תשאלו אותם, אבל עד עכשיו אף אחד לא התלונן. |
| הכלי מאפשר חיסכון בזמן. הוא גם מפשט תהליכים. בנוסף, הוא משפר את חוויית המשתמש. | הכלי חוסך זמן. כמה? תלוי. אבל מספיק כדי שתרגישו את זה. |

Vary sentence length. Drop in a one-word sentence. Leave a thought hanging.

### T8 — English Syntax in Hebrew Clothes

The grammar is correct but the sentence was clearly thought in English first.

| Tell | Fix |
|------|-----|
| זה לא רק על הכסף, זה על העיקרון | הכסף זה לא העניין. העיקרון כן. |
| ישנם מספר גורמים שיש לקחת בחשבון | יש כמה דברים שצריך לחשוב עליהם |
| עם זאת, ישנם אתגרים משמעותיים | אבל יש גם בעיות |
| אנחנו שמחים להודיע על השקת... | יש לנו משהו חדש |

Watch for: "ישנם" constructions, "זה לא רק X, זה גם Y" parallelisms, "עם זאת" / "יתרה מכך" connectors.

### T9 — Exclamation Inflation

In English, ! is casual. In Hebrew, it's loud. AI treats them like English.

| Tell | Fix |
|------|-----|
| הפתרון המושלם!! | הפתרון עובד |
| הצטרפו עכשיו! | ההרשמה פתוחה |

One ! per page is plenty.

### T10 — Foreign Typography

Small details that break the illusion of native text.

| Element | AI default | Hebrew |
|---------|-----------|--------|
| Quotes | "text" (curly English) | ״text״ or "text" (straight) |
| Acronyms | צה"ל | צה״ל (gershayim ״) |
| Abbreviations | פרופ, ד"ר | פרופ׳, ד״ר (geresh ׳ for abbreviations) |
| And | X & Y | X ו-Y |
| Hash | #מספר | spell it out |

### T11 — Compulsive Bullet Lists

AI breaks everything into bullets. Bullets are for checklists, steps, specs. When you're explaining or persuading, a sentence reads better.

| Tell | Fix |
|------|-----|
| היתרונות: • חוסך זמן • קל לשימוש • עובד מכל מקום | חוסך זמן, קל לשימוש, ועובד מכל מקום. |
| מה תקבלו: • ליווי אישי • תרגול מעשי • כלים להמשך | תקבלו ליווי אישי, תתרגלו על דברים אמיתיים, ותצאו עם כלים שעובדים. |

If it reads naturally as a sentence — write a sentence.

---

## Writing Principles

What to aim for — not just what to avoid.

### P1 — Write How People Talk

Not how textbooks read. Not how press releases sound. How a person explains something to another person.

| Written-for-a-committee | Spoken |
|------------------------|--------|
| יצירת חוויה מיטבית | לגרום לזה להרגיש נכון |
| מתן מענה | לעזור |
| ביצוע אופטימיזציה | לשפר |

If it sounds like a government form, rewrite it.

### P2 — Verbs Over Nouns

Hebrew becomes lifeless with abstract nouns. Verbs bring it back.

| Noun-heavy | Verb-driven |
|-----------|-------------|
| העצמה של צוותים | לעזור לצוות לעבוד טוב יותר |
| יצירת ערך | להיות שימושי |
| מתן מענה מקיף | לפתור את הבעיה |

### P3 — Tighten Without Drying

Cut the padding. Keep the warmth.

| Padded | Tight |
|--------|-------|
| אנחנו שמחים להודיע לכם על השקת המוצר החדש שלנו | יש לנו מוצר חדש |
| במסגרת הפעילות שאנחנו מובילים בתחום | (cut entirely) |
| חשוב לדעת שבעת האחרונה | לאחרונה |

### P4 — Start With the Thing, Not the Setup

AI has a handful of go-to openings. All of them stall.

**Detect:** "בעולם שבו...", "בעידן של...", "תארו לעצמכם...", "כולנו מכירים את הרגע ש...", "האם אי פעם תהיתם..."

Start with a fact, a moment, a question. "אתמול", "ניסיתי", "יש בעיה". Walk in through the back door.

### P5 — Talk at Eye Level

Hebrew shuts down when you lecture. It opens up when you talk like a peer.

| Lecturing | Eye-level |
|-----------|-----------|
| חשוב שתבינו | (just explain) |
| כדאי לזכור | (just say it) |
| אל תטעו לחשוב ש | (let them think) |

### P6 — Be Specific, Not Enthusiastic

Israeli readers detect fake excitement immediately. Replace adjectives with evidence.

| Hype | Proof |
|------|-------|
| כלי מדהים | חוסך שעתיים ביום |
| פתרון מטורף | הכפיל את ההמרות |
| חוויה מושלמת | 94% מרוצים |

### P7 — Less Is More

One clear metaphor sticks. Five in one paragraph sound like a poetry slam. Same with explanations — don't spell out every implication. A half-open thought invites the reader in.

| Over-explained | Room to breathe |
|---------------|----------------|
| הכלי חוסך זמן, מפשט תהליכים, ומאפשר לכם להתמקד במה שחשוב | הכלי חוסך זמן. מה תעשו עם הזמן הזה? זה כבר עליכם. |

---

## Hebrew-Specific Grammar Traps

Things AI gets wrong that a native speaker catches instantly.

### G1 — "גם" Placement

"גם" goes BEFORE the word it emphasizes. AI almost always gets this wrong.

| Wrong | Right | Because |
|-------|-------|---------|
| תבנה לי **גם** צוות | תבנה **גם לי** צוות | emphasis on "for me too" |
| אני **גם** רוצה | **גם אני** רוצה | emphasis on "me too" |

Read it out loud. Where does the stress land? That's where גם goes.

### G2 — English Connectors

| English pattern | Hebrew pattern |
|----------------|---------------|
| עכשיו, זה לא עבד... | האמת, זה לא עבד... |
| אז, הנה מה שקרה | (just start with what happened) |
| בעצם, מה שאני אומר הוא | (just say it) |

If it reads like a dubbed show — rewrite.

### G3 — Corporate Loan Words

Some borrowed terms are standard in their industry — "סטארטאפ" and "פידבק" are just Hebrew now. The problem is when AI stacks corporate jargon where plain Hebrew would land better. Use judgment: if the term is what your audience actually says, keep it. If it's dressing up a simple idea, simplify.

| Jargon | Plain Hebrew |
|--------|-------------|
| סינרגיה | שיתוף פעולה |
| אימפקט | השפעה |
| אופטימיזציה | שיפור |
| אקוסיסטם | מערכת / סביבה |
| פתרון מקצה לקצה | מטפל בהכל |
| מענה הוליסטי | פתרון שעובד |

### G4 — Translated Enthusiasm

English-to-Hebrew tone mapping:

```
"I'm SO excited to share this!"
→ "יש לי משהו ששווה לכם לשמוע."

"This game-changing framework will transform your business!"
→ "השיטה הזו עובדת. בדקתי."

"Don't miss this amazing chance to level up!"
→ "ההרשמה נסגרת ביום חמישי."
```

### G5 — Ktiv Maleh Errors

AI misspells common words by dropping vav or yod. Native readers catch this instantly.

| Wrong | Right | Rule |
|-------|-------|------|
| תכנה | תוכנה | vav for /o/ |
| שרות | שירות | yod for /i/ |
| תקשרת | תקשורת | vav for /o/ |

When in doubt, follow Academy of Hebrew Language ktiv maleh standard: if you hear /o/, there's a vav; if you hear /i/, there's a yod.

### G6 — Humor

Israeli humor is a raised eyebrow, not a punchline. It sounds like you said something to yourself and someone overheard. Dry. Almost accidental.

If you're constructing a setup-punchline joke — you're trying too hard.

---

## Quality Check

Run this before delivering any Hebrew text.

| # | Check | Pass? |
|---|-------|-------|
| 1 | Read it out loud. Would a person say it this way? | |
| 2 | Any em dashes? | |
| 3 | Any parenthetical English? | |
| 4 | Gender mismatch? (audience address AND narrator voice) | |
| 5 | Filler phrases? Count them. | |
| 6 | Compulsive summary at the end? | |
| 7 | Triads? (three adjectives, three benefits) | |
| 8 | Every sentence the same length? | |
| 9 | English syntax in Hebrew words? | |
| 10 | More than one ! per section? | |
| 11 | Corporate loan words? | |
| 12 | Talking down instead of at eye level? | |
| 13 | Ktiv maleh errors? (missing vav/yod) | |
| 14 | Bullet lists where a sentence would do? | |

3+ failures → rewrite from scratch. Don't patch.

---

## Before / After

### Marketing copy

**Before:**
```
אנחנו שמחים להציג את הפלטפורמה החדשנית שלנו שמאפשרת אופטימיזציה
של תהליכי עבודה. הפלטפורמה מספקת מענה מקיף, מתקדם ויעיל לאתגרים
העסקיים של היום! חשוב לציין כי הפתרון מתאים למגוון רחב של עסקים.
```

**After:**
```
בנינו כלי שעושה סדר בעבודה. הוא לא עושה הכל, אבל את מה שהוא
עושה — הוא עושה טוב. תנסו.
```

**What changed:** Killed filler ("חשוב לציין"), killed triad ("מקיף, מתקדם ויעיל"), killed corporate ("אופטימיזציה", "מענה"), killed hype ("שמחים להציג", "!"), added human voice ("תנסו").

### Newsletter opening

**Before:**
```
שלום לכם! יש לנו חדשות מרגשות! השבוע השקנו פיצ'ר חדש ומדהים
שישנה לחלוטין את הדרך שבה אתם עובדים. אנחנו בטוחים שתאהבו אותו!
```

**After:**
```
יש משהו חדש. עבדנו על זה שלושה חודשים ועכשיו אפשר סוף סוף לספר.
בקצרה: שינינו את הדרך שבה עובד ה[פיצ'ר]. ההסבר הארוך למטה.
```

**What changed:** Killed translated enthusiasm ("חדשות מרגשות!"), killed empty hype ("מדהים", "לחלוטין"), killed presumption ("אנחנו בטוחים שתאהבו"), added specificity ("שלושה חודשים"), added human pacing.

### Product explanation

**Before:**
```
המערכת שלנו — פתרון חדשני (Innovative Solution) — מאפשרת ייעול
תהליכים ארגוניים. חשוב לציין כי היא פועלת באופן רציף ומספקת תוצאות
איכותיות, מדויקות ואמינות. לסיכום, מדובר בכלי שמתאים לכל ארגון.
```

**After:**
```
המערכת רצה ברקע ועושה את שלה. כמה היא חוסכת? תלוי. אולי שעתיים
ביום, אולי פחות. העניין הוא שלא צריך לחשוב על זה.
```

**What changed:** Killed em dash, killed parenthetical English, killed filler ("חשוב לציין"), killed triad ("איכותיות, מדויקות ואמינות"), killed compulsive closer ("לסיכום"), killed corporate ("ייעול תהליכים ארגוניים"), added specificity ("שעתיים ביום"), added human uncertainty ("תלוי").

