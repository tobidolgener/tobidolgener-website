# 01 · Team Charter and Working Toolkit — SAGA-AGENT

*Competency: Teamwork — work effectively as a team on an AI-assisted project, sharing
roles, decisions and knowledge so that everyone can build, test and explain the app.*

## 1. Purpose

We build SAGA-AGENT: a social-media agent that writes on-brand posts for small
businesses and publishes nothing without the owner's approval. We build it with an
AI builder (Claude Code) and follow the SDLC: Requirements → Design → Development →
Testing → Deployment → Maintenance.

**Our guiding sentence:** *"It proposes. You press the button."*
("Er schlägt vor. Du drückst ab.")

## 2. Roles

| Role | Who | Responsibilities |
|---|---|---|
| Product owner / client liaison | Tobias Dolgener | Talks to the client, decides priorities, approves every release |
| AI director ("prompt lead") | Tobias Dolgener | Writes build instructions, keeps the project instructions file current, reviews AI output |
| AI builder | Claude Code | Writes code and tests in small steps, explains what it changed, reports its own mistakes |
| Tester | [TBC — team member] | Runs the user journeys on a real phone, logs bugs in the bug log |
| Documentation & presentation | [TBC — team member] | Keeps PRD, design pack and build log in sync with the product |

> If the team is a single human plus the AI builder, each human role above is held by
> Tobias. Every team member must still be able to explain the app (Showcase rule).

## 3. Decision rules

1. **The client decides *what*, we decide *how*.** Client decisions are written down
   with the date (e.g. "Client 08.09: onboarding runs on our AI key").
2. **The AI proposes, a human approves.** No deploy, deletion or message to a real
   user without explicit human approval — the same rule the product applies to its users.
3. **Think first, then build.** For anything larger than a small fix the AI builder
   presents a plan and waits for "go" ("erst denken", "erst bestätigen, nichts bauen").
4. **Disagree with evidence.** If the AI thinks a client request is risky it says so,
   with a measurement (example: warning that 400 users on one AI key will hit rate
   limits and create an uncapped bill).

## 4. Ways of working

| Rhythm | What |
|---|---|
| Per change | Plan → build one small step → automated tests ("gates") → counter-check → deploy |
| Daily | Short status: what is live, what is open, what is blocked |
| Weekly (Friday) | Present progress, collect client feedback |

**Language:** team communication in German; course documents in English.

## 5. Working toolkit

| Need | Tool |
|---|---|
| AI builder | Claude Code (desktop app, local repository) |
| Source code | Local git repository `saga-agent` (commit yes, push to a public remote no) |
| Hosting | Own Linux server (EU, Hetzner), web service behind Caddy |
| Deployment | One script only: `ausrollen.sh` (runs all tests locally *and* on the server first) |
| Database | Postgres in production, SQLite for local development |
| Payments | Stripe |
| Publishing | Zernio (social-posting API: LinkedIn, Instagram, Facebook, TikTok) |
| AI models | Claude, Gemini or OpenAI behind one engine interface |
| Mail | SMTP |
| Knowledge | Memory files per topic, handover files between chats |

## 6. Team rules (non-negotiable)

- **No secrets in chat** — keys, passwords and tokens never appear in a message or a screenshot.
- **Never delete** data or files without explicit approval.
- **Never push** to a remote; deploy only via the deploy script.
- **Tests check behaviour, not source code.** A test that only looks for a string in the code is not a test.
- **One test run at a time** — never build while a test run is in progress.
- **Report mistakes openly.** The AI builder names its own errors (it did, repeatedly).
- **Truthfulness:** the current state comes from the system, never from a document.

## 7. Knowledge sharing

- Every finished round ends with a short handover note (what changed, why, what is open).
- Rules learned the hard way go into the project instructions file (see 04), so the
  next chat — or the next teammate — starts with them.
- A catalogue of recurring test-failure types (36 types) is kept as a memory file.
