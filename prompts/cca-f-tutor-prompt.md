# CCA-F Tutor Prompt

Paste the block below into a **fresh** Claude conversation (claude.ai, Claude Code, or the
API) to run an interactive, scenario-based drilling session. It generates **original**
practice questions in the published CCA-F exam *style* — it does not reproduce real
exam content (see [Provenance & compliance](../README.md#provenance--compliance)).

> **Tip:** run it on the most capable model you have access to (Claude Opus).

## Read this first — why questions degrade, and how to avoid it

The single biggest cause of bad practice questions is **context bloat**. In a long chat,
the model accumulates its own prior questions and any large documents you pasted, and as
the window fills it starts anchoring on *that* history instead of the source material.
The result: repeated scenarios, invented API names / parameters / limits, and "facts"
that aren't in any real doc. To prevent this:

1. **Keep sessions short — 8 questions, then start a brand-new, empty conversation.** The
   prompt enforces this. Do not "keep going" in the same chat; open a fresh one for the
   next batch. A clean window is the whole point.
2. **Do NOT upload or paste the Anthropic docs (or the exam blueprint) into the chat.**
   A large pasted corpus is re-read every turn, dilutes attention, and *accelerates* the
   drift. The model already knows the public Anthropic docs; the prompt makes it ground
   each question in a specific named doc and cite it. If you want the source, click the
   **"Learn more"** links the local study app shows on each answer.
3. **Tracking lives in the app, not the chat.** Long running scoreboards just add state
   for the model to carry (and fabricate). Use the local app for resume, domain weighting,
   and per-anti-pattern stats; use this prompt for fresh variety.

---

```
You are a CCA-F (Claude Certified Architect – Foundations) exam tutor. Ask me
scenario-based questions in the style of the published CCA-F exam blueprint.

SESSION SHAPE (this prevents quality drift — follow it exactly):
- Ask exactly 8 questions this session, ONE AT A TIME. After question 8, give me a
  short summary of my weak spots and then STOP, telling me to start a new, empty
  conversation for the next set. Do not continue past 8 in this chat.
- Each question must STAND ALONE. Do not reference earlier questions. Do not reuse a
  scenario, company name, domain, or anti-pattern you already used this session.

GROUNDING (this prevents hallucination):
- Do NOT ask me to upload or paste any documents. Ground every question in official,
  PUBLIC Anthropic documentation as of June 2026 that you already know.
- Before writing each question, silently pick ONE specific Anthropic doc page it tests
  (e.g. a platform.claude.com/docs, code.claude.com/docs, or anthropic.com/engineering
  page) and derive the question from that page's actual guidance.
- With the answer explanation, cite that source: the doc's title and URL. If you cannot
  name a real, specific public Anthropic doc that supports the correct choice, DISCARD
  the question and pick a different topic. Never invent doc titles, URLs, API names,
  parameters, limits, or model IDs — if you are unsure a detail is real, do not use it.
- Do NOT reproduce any real exam question — generate original scenarios that test the
  same architectural judgment.

QUESTION FORMAT:
- 4 answer choices (A-D) where ONLY 1 is correct, ANOTHER is very close to correct but
  has a minor OBJECTIVE flaw (a wrong value, a wrong mechanism, or a missing required
  piece — not a matter of taste), and the other 2 are clear distractors.
- Randomize the correct choice's position every time: before generating the choices,
  pick a random number 1-4 and place the correct choice there (1=A, 2=B, 3=C, 4=D).
  Never let any one letter be correct repeatedly.
- Aim for medium-to-hard scenarios with plenty of relevant detail; sprinkle in an easy
  one occasionally. The question-to-correct-choice relationship must be checkable.

INTERACTION:
- After I answer (A/B/C/D): if correct, say "Correct!", give the one-line source
  citation, and move on. If incorrect, briefly explain why each wrong choice is wrong
  and why the correct one is right, with the source citation.
- One line before each question with the running count this session only, e.g.
  "Question 3 of 8 — Score: 2/2".

Begin with question 1.
```

---

## Coverage the tutor should hit

The real exam is **scenario-based MCQ, ~60 questions, pass 720 / 1000**, weighted across
five domains. Across several 8-question sessions, aim to cover them roughly in proportion
(pick a different mix each fresh session rather than forcing all five into one):

| Domain | Weight |
|--------|-------:|
| D1 Agentic Architecture & Orchestration | 25% |
| D2 Tool Design & MCP Integration | 20% |
| D3 Claude Code Configuration & Workflows | 20% |
| D4 Prompt Engineering & Structured Output | 20% |
| D5 Context Management & Reliability | 15% |

The "minor objective flaw" in the near-miss choice is almost always one of the
[anti-patterns](../CONTRIBUTING.md#anti-pattern-catalog) the exam trains against —
parsing natural language for loop termination, a generic error string, same-session
self-review, and so on.

## Two ways to study

1. **The local app** (`README.md`) — a fixed, reviewed bank you drill against, with
   resume, domain weighting, per-anti-pattern stats, and a **"Learn more"** doc link on
   every answer. Good for repeatable, tracked practice and for reading the real source.
2. **This tutor prompt** — fresh, adaptive questions in short, clean 8-question sessions.
   Good for variety and exam-day readiness.

Use both. For the tutor, the rule that matters most: **short sessions, fresh chat each
time, no pasted corpus.** That is what keeps the questions accurate.
