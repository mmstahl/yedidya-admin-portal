---
name: landing-page-design
description: Design high-converting, visually distinctive landing pages. Use when the user needs a landing page, marketing page, product page, or any single-page site meant to convert visitors. Covers structure, visual direction, section design, and conversion principles. Use this whenever someone mentions landing page, marketing site, product page, homepage, or conversion-focused web design.
---

# Landing Page Design

Design landing pages that convert visitors and look like a human designed them. This skill covers structure, visual direction, and conversion design — not copy (that's the writer's job) or implementation (that's the frontend-dev's job).

**Your output is a design spec** that the writer uses for content direction and the frontend-dev uses for implementation. Be specific enough that both agents can work independently from your spec.

## Before You Start

1. Read core files — `core/tone-of-voice.md`, `core/user-identity.md`, `core/project-brief.md` — to understand the brand.
2. **Identify the single goal.** Every landing page has one conversion action. Not two. Not "explore our services." One thing: sign up, book a call, buy, download. If unclear, ask.
3. **Identify the audience.** Who lands here? What's their state of mind? Problem-aware or solution-aware? Cold traffic or warm referral? This shapes everything from section order to tone.
4. **Define the design system** (see below) before touching layout.

## Design System — Define First

Don't start with sections. Start with the system. Every element on the page should feel like it belongs to the same family.

### Typography

Two fonts maximum. A display font for headlines and a body font for text.

Avoid the AI defaults — Inter, Roboto, Open Sans. They scream "template." Choose fonts that match the brand personality:

| Brand feel | Font direction |
|-----------|---------------|
| Professional, trustworthy | Serif headlines (Fraunces, Playfair) + clean sans body |
| Modern, technical | Geometric sans (Space Grotesk, Satoshi) |
| Warm, approachable | Rounded sans (Nunito, Plus Jakarta Sans) |
| Bold, high-energy | Heavy condensed display (Bebas Neue, Oswald) |
| Creative, editorial | Italic serif display (Instrument Serif, Cormorant) + monospace-tinged body |

Define a full type scale — not just font names. Specify sizes, weights, and line heights for: hero headline, section headlines, sub-headlines, body, small text, and CTA buttons. Include both desktop and mobile sizes.

Headlines: 2.5-4rem minimum. Don't be timid with type size — large type anchors sections and creates hierarchy without decoration.

### Color Palette

Three layers:
- **Dominant (60%)** — background and large areas. Usually neutral.
- **Brand (30%)** — headings, cards, secondary elements.
- **Accent (10%)** — CTAs, highlights, interactive elements.

Specify hex codes for every color. Include hover states for interactive elements.

The accent color goes on the CTA and nowhere else that competes with it. If the CTA doesn't visually pop from 2 meters away, the palette isn't working.

**Dark vs. light pages:** A dark background (near-black or deep saturated color) works for creative, technical, and premium brands. Light backgrounds (warm off-white, not pure white) work for approachable, warm, and service-oriented brands. The 60-30-10 rule applies to both — on dark pages, the accent pops even harder, so use it with even more restraint.

### Spacing

Use an 8px base unit. Define spacing tokens from tight (8px) to generous (128px+).

Generous whitespace between sections. Tight spacing within sections. The contrast between "breathing room" and "grouped content" creates visual hierarchy without decoration.

Section padding should be at least 2x the padding between elements inside the section. Define both desktop and mobile section padding.

Set a max content width (typically 1100-1200px) and a max text width for readability (typically 640-680px).

### Border & Shape Language

Define the shape vocabulary upfront — it affects how the page feels:
- **Sharp corners** (0-2px radius) → editorial, gallery-like, intentional
- **Subtle rounding** (4-8px) → professional, modern, approachable
- **Full rounding** (100px/pill) → playful, consumer, friendly

Pick one direction and be consistent. Cards, buttons, and images should share the same language. If everything has the same border-radius, it looks systematic; if one element breaks the pattern (e.g., pill-shaped CTA on an otherwise sharp-cornered page), it draws attention.

### Motion Strategy

Decide upfront — one approach, don't mix:

- **Minimal:** Subtle hover states, smooth scrolling. Safe, clean.
- **Moderate:** Scroll-triggered reveals, micro-interactions on CTAs. Good balance.
- **Expressive:** Parallax, animated backgrounds, staggered entrances. High-end feel, higher risk of looking overcooked.

Specify exact durations, easing curves, and what triggers each animation.

## Aesthetic Direction

Pick a direction before designing. This prevents the generic "AI landing page" look.

**Minimalist & Refined** — Lots of whitespace, restrained palette, elegant typography. Works for: premium services, professional tools.

**Bold & Graphic** — Strong color blocks, oversized type, graphic elements. Works for: startups, creative tools, anything that needs energy.

**Editorial** — Magazine-like layout, editorial photography, sophisticated grid. Works for: media, luxury, content-heavy brands.

**Organic & Warm** — Soft colors, rounded shapes, textures. Works for: wellness, education, personal brands.

**Dark & Technical** — Dark backgrounds, monospace accents, terminal-like elements. Works for: developer tools, tech products.

These can blend — "Minimalist with Organic warmth" or "Bold meets Editorial" — but name the primary direction and explain why it fits the brand. Don't just pick one; justify the choice based on audience and conversion goal.

### Anti-Patterns: The "AI Landing Page" Look

These patterns signal "generated, not designed." Avoid all of them:

| Pattern | Why it fails |
|---------|-------------|
| Purple/blue gradient on white | Used by every AI-generated page |
| Symmetric 3-column feature grid | Feels like a template, not a design |
| Generic line icons from one pack | No personality |
| Stock photos of diverse teams smiling | Instantly reads as fake |
| Centered everything | No visual tension, no hierarchy |
| Rounded cards with subtle shadows | The default component-library look |
| Inter or Roboto everywhere | Default font = default feel |

**The fix:** Introduce at least one element of asymmetry, one unexpected design choice, and one moment where the layout breaks the grid. Human designers do this instinctively. AI doesn't — so this is what separates designed from generated.

Name your unexpected design moments explicitly in the spec so the frontend-dev knows they're intentional, not bugs.

## Page Structure

Section order matters. Each section has a job. Wrong order = lost momentum.

| Order | Section | Job | Skip when |
|-------|---------|-----|-----------|
| 1 | **Hero** | Hook + primary CTA | Never |
| 2 | **Social proof bar** | Instant trust | No logos or numbers yet |
| 3 | **Problem** | Make the pain real | Audience is already solution-aware |
| 4 | **Solution / Features** | Show how you solve it | Never |
| 5 | **How it works** | Reduce perceived complexity | Product is self-explanatory |
| 6 | **Testimonials** | Proof through others | Zero testimonials exist |
| 7 | **Pricing** | Enable decision | Pricing is custom or complex |
| 8 | **FAQ** | Handle objections | Product is very simple |
| 9 | **Final CTA** | Capture the undecided | Never |

Hero and final CTA are non-negotiable. Everything between serves the journey from "what is this?" to "I'm in."

**Adapt the structure to the business type.** A portfolio page might replace Problem/Solution with case studies. A pre-launch product skips social proof and testimonials. A service business might combine Problem and Solution into a transformation narrative. The table is a starting framework — use judgment, and explain any deviations in the spec.

## Section Design Guide

For each section in your spec, provide:
1. **Layout** — columns, alignment, grid behavior (desktop and mobile)
2. **Visual specs** — backgrounds, spacing, specific measurements
3. **Content direction** — what the writer should produce (topic, length, tone), NOT the actual copy. You're the designer, not the writer. Give enough direction that the writer knows what to produce for each element (headline territory, subheadline scope, number of pain points, etc.)
4. **Image/visual direction** — what kind of visuals belong here (photography style, illustration approach, mockup treatment). Enough detail that someone could brief a photographer or illustrator.
5. **Mobile behavior** — how the section transforms on small screens

### Hero

The hero decides everything. Visitors decide to stay or leave before scrolling.

**Required elements:**
- Headline (benefit-focused, 6-12 words)
- Subheadline (expands on how, 15-25 words)
- Primary CTA button
- One visual (product shot, illustration, or contextual image)

**Layout options** — don't default to text-left / image-right every time:
- Full-width visual with overlaid text
- Centered headline with visual below
- Video background with minimal overlay
- Asymmetric composition with dynamic whitespace
- Image bleeding off the viewport edge (creates tension)

**The squint test:** Squint at the hero until you can barely see it. Can you still tell what the page is about? Is the CTA the brightest element? If not, fix the hierarchy.

### Social Proof Bar

Immediately after the hero. Quiet — this section reassures, it doesn't compete with the hero.

"Trusted by 10,000+ teams" with 4-6 logos. Grayscale, small, evenly spaced. That's it.

For pre-launch: skip logos. Use a metric ("500+ on the waitlist") or a single quote from a beta user. If you have nothing — skip the section entirely and embed credibility signals elsewhere (specific numbers in features, transparency in FAQ).

### Problem Section

Make the visitor's pain tangible. Their language, not yours. One clear problem — not a list of everything wrong with the world.

**Design:** This section should feel different from the solution section. If the solution is bright and optimistic, the problem is darker or more muted. A background color shift (light-to-dark or vice versa) reinforces the before/after contrast.

### Solution / Features

3-4 features maximum. Each gets:
- A clear name
- One sentence explaining the benefit (not the technical feature)
- A visual (screenshot, illustration, or icon — not from generic icon packs)

**Layout options:**
- Alternating rows (feature/visual, then swap) — break the 50/50 split on at least one row
- Bento grid (unequal card sizes — not a uniform 3-column grid)
- Single scrolling showcase with sticky text

### How It Works

3 steps. If the process has 7 steps, abstract to 3. Numbered, with clear visual progression. Horizontal on desktop, vertical on mobile. Connect steps visually (line, arrow, or progression indicator).

### Testimonials

2-3 maximum. Each needs:
- A specific quote (not "Great product!")
- Name and role
- Photo (real, not stock)

Highlight the key phrase in each — the one line that makes someone think "that's me."

Don't display testimonials in a uniform row. Offset cards, vary sizing, or use an asymmetric layout.

### Pricing

If included:
- 2-3 tiers maximum
- Highlight recommended tier visually (border, badge, subtle scale difference)
- Monthly/annual toggle with savings shown
- CTA per tier with specific text

### FAQ

5-7 questions. Accordion format. Answer the real objections: "Is this right for me?", "What if it doesn't work?", "How is this different from X?"

A two-column layout (sticky headline on the left, accordion on the right) works well on desktop and collapses cleanly to single-column on mobile.

### Final CTA

Full-width. Contrasting background. Repeat the primary CTA with urgency or a different angle.

This is the most visually dramatic section. If the page is light, this section goes dark (or vice versa). If the page is minimal, this gets the most visual weight. It catches people who read everything but haven't committed yet.

## Navigation & Footer

These are part of the design. Don't leave them to the frontend-dev to figure out.

### Navigation

**Sticky. Minimal. Always has the CTA.**

- Logo or name on the left
- Primary CTA button on the right (smaller than the hero CTA, same accent color)
- Avoid nav links on single-page conversion pages — they dilute focus. If absolutely necessary, one or two anchor links max
- Background: transparent on load, transitions to solid (with backdrop blur) on scroll
- Mobile: same layout, no hamburger menu (there's nothing to put in it)

The CTA in the nav ensures conversion is always one click away at any scroll position.

### Footer

Minimal. Not a sitemap.

- Brand name, copyright, essential legal links (privacy, terms)
- Optionally one or two social links
- Match or extend the final CTA's background color for visual continuity
- No multi-column mega-footer — this is a landing page, not a marketing site

## Conversion Design Principles

### Visual Hierarchy

The eye follows: Headline → Subheadline → CTA → Social proof. If anything else competes, it's wrong.

**One primary CTA per viewport.** The CTA button should be the most visually prominent element on screen at any scroll position. If a decorative element draws more attention — remove it or tone it down.

### CTA Button Design

| Rule | Why |
|------|-----|
| High contrast with background | Must be the most visible element |
| Minimum 48px height | Tap target for mobile |
| Generous horizontal padding | Too-tight buttons look clickable but unimportant |
| Consistent style across the page | Same color, same shape, every time |
| Whitespace around it | Don't crowd the CTA — let it breathe |

One primary CTA style. One optional secondary (text link or ghost button). No third option.

**CTA text direction:** Tell the writer to use action-specific text ("Book Your Free Call", "Join the Waitlist") — not generic ("Get Started", "Learn More", "Submit").

### Form Design

Every field reduces conversion by roughly 10%. Ruthlessly minimize:
- **Sign-up:** Email only. Maybe name.
- **Booking:** Name + email + one qualifying question.
- **Contact:** Name + email + free-text message.

Single column. Inline validation. Button text = the action ("Book Your Call", not "Submit").

For pre-launch waitlists, an inline email input + button in the hero (not a separate form) reduces friction.

### Trust Signal Placement

Place trust signals near decision points:
- Logos below the hero (immediate trust)
- Testimonials before pricing (proof before commitment)
- Security badges near forms (reduce anxiety)
- Guarantee near final CTA (reduce risk)
- Micro-copy below CTAs ("No credit card required", "30 min, no commitment")

## Responsive Design

Design for mobile first, expand to desktop. Not the other way around.

| Rule | Why |
|------|-----|
| CTA full width on mobile | Easy to tap |
| Sticky CTA on scroll | Always accessible |
| Font minimum 16px | iOS zooms inputs below 16px |
| Tap targets 48x48px minimum | Accessibility standard |
| Single column | Don't fight the narrow viewport |
| Simplify hero on mobile | Less text, smaller image, CTA visible |
| Lazy-load below-fold images | Performance on mobile networks |

**Define breakpoints** in the design system (typically: mobile <768px, tablet 768-1279px, desktop 1280px+). Specify how each section transforms at each breakpoint.

**Sticky mobile CTA:** On mobile, add a fixed bottom bar with the CTA that appears after the hero scrolls out of view and hides when the final CTA section is visible. This ensures the conversion action is always one tap away.

## Output Structure

Save to `output/landing-page-design-[short-topic].md`. Use this structure:

```
# Landing Page Design Spec — [Project Name]

## Overview
[Business, conversion goal, target audience, audience state of mind]

## Design System
[Typography (with full type scale), color palette (with hex codes), spacing tokens, border/shape language, motion strategy]

## Aesthetic Direction
[Direction chosen and why, key aesthetic commitments, unexpected design moments planned]

## Page Structure
[Section order table with include/skip rationale]

## Section Specs
[For each section: layout, visual specs, content direction for writer, image direction, mobile behavior]

## Navigation & Footer
[Nav and footer design specs]

## Responsive Summary
[Table showing how each element behaves at each breakpoint]

## Quality Checklist
[Fill in the checklist below with status and notes]
```

## Quality Checklist

Before handing off:

| # | Check |
|---|-------|
| 1 | Single conversion goal — every section serves it? |
| 2 | Design system fully defined (fonts with scale, colors with hex, spacing tokens, shape language, motion)? |
| 3 | Hero passes the squint test? |
| 4 | CTA is the most visible element at every scroll position? |
| 5 | 3-4 features maximum, not a feature dump? |
| 6 | At least one asymmetric or unexpected design moment? |
| 7 | No AI aesthetic anti-patterns (purple gradients, symmetric grids, stock photos)? |
| 8 | Mobile layout specified for every section? |
| 9 | Trust signals placed near decision points? |
| 10 | Visual contrast between problem and solution sections? |
| 11 | Final CTA is visually dramatic — different from the rest of the page? |
| 12 | Forms have the minimum possible fields? |
| 13 | Section order follows the structure table (or has a justified reason not to)? |
| 14 | Content direction provided for every text element (for the writer)? |
| 15 | Image/visual direction specified for every visual element? |
| 16 | Navigation includes sticky CTA? |
