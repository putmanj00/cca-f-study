# Prompts

Reusable prompts for CCA-F study.

| File | What it does |
|------|--------------|
| [`cca-f-tutor-prompt.md`](cca-f-tutor-prompt.md) | An interactive AI tutor that asks 60 original, scenario-based questions one at a time, scores you, and coaches you on the mistake patterns it notices. |

## How to use the tutor prompt

1. Open a fresh conversation with Claude (claude.ai, the Claude Code CLI, or the API).
2. Copy the fenced prompt block from `cca-f-tutor-prompt.md` and send it.
3. Answer each question with a single letter (A/B/C/D).
4. The tutor replies "Correct!" or explains every choice, keeps a running score, and
   periodically tells you where you're weak.

These questions are **generated fresh each session** and are grounded in public
Anthropic documentation and the published exam blueprint — they are study aids in the
exam's *style*, not copies of real exam content. See the repo
[README](../README.md#provenance--compliance) for the provenance policy.
