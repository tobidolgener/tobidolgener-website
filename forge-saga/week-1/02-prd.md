# 02 · Product Requirements Document — SAGA-AGENT

*Competency: Explanation & evaluation — turn a loosely defined client need into clear,
testable requirements, and justify how the solution fits the client's real problem.*

| | |
|---|---|
| Product | SAGA-AGENT ("Product 4" of the ANVIL product line) |
| Version | 1.0 (reconstructed baseline, as of 20.09.2026) |
| Source | Product briefing 19.08.2026; client decisions 03.09–11.09.2026 |
| Owner | Tobias Dolgener |

## 1. The client's loosely described problem

> "Small businesses should get a social-media agent of their own — with their name,
> their voice, their photos and a constitution they approve themselves."

What the client *said*: "We need social-media posts without spending evenings writing them."
What the client *needed* (found out through interviews and a test evening with a real user):

1. Posts that sound like **their** business, not like generic AI text.
2. **Control:** nothing goes out that they have not seen and approved.
3. **No technical hurdle on day one.** A tradesperson who is asked for an API key in
   step two is lost ("Wer am ersten Tag einen API-Schlüssel verlangt, verliert den
   Handwerker im zweiten Schritt." — Client, 08.09).
4. **Legal safety:** AI-generated content must be labelled (EU AI Act), no invented facts,
   no promises of reach or revenue.

## 2. Users

| Persona | Description | Main goal |
|---|---|---|
| **Owner** ("Mandant") | Small-business owner, e.g. *Chris, independent financial adviser*; uses a phone, little time, no tech background | Approve good posts in seconds |
| **Test user** | Invited colleague of the pilot client; runs on the operator's AI key | Try SAGA without paying or setting up keys |
| **Operator** | Pathfinders (CEO) | See tenants, help, invite test users, keep costs under control |

## 3. Scope

**In:** multi-tenant web portal (mobile-first, installable on the home screen), guided
onboarding, brand constitution, post drafting (text, image post, carousel), approval,
publishing via Zernio, own rules per tenant, usage/cost tracking.
**Out:** a native app, auto-posting without approval, ad management, analytics/reach promises.

## 4. Requirements (MoSCoW)

Each requirement has an acceptance test ("gate"). IDs are referenced in the design pack and test plan.

### Must have

| ID | Requirement | Acceptance criterion |
|---|---|---|
| M1 | **Tenant separation.** Each business sees only its own data, keys and posts. | A tenant requesting another tenant's draft ID gets 404; a key encrypted for tenant A cannot be decrypted for tenant B. |
| M2 | **Login without password** via a single-use magic link (valid 30 min) or passkey (Face ID / fingerprint). | Link works once; a second click is rejected; after 30 min it is rejected. |
| M3 | **The login page never reveals whether an e-mail is registered.** | Known and unknown address get identical responses. |
| M4 | **No approved constitution → no writing.** ("Ohne Freigabe schreibt SAGA-AGENT keine Zeile.") | Draft request for a tenant with `freigegeben=false` is refused in code, not just hidden in the UI. |
| M5 | **Never invent facts.** Missing facts become a visible `[[placeholder]]`. | Fact-check gate flags invented numbers/names; post with placeholder cannot be published. |
| M6 | **AI label `#KIunterstuetzt` under every post** (EU AI Act, since 02.08.2026). Cannot be switched off. | Label presence is *measured* in the final text, not judged by a model. |
| M7 | **Approval before publishing.** Every post needs "Approve & hand over". | No code path publishes a draft without an approval record. |
| M8 | **Guided onboarding** that ends in an approved brand constitution. | A new tenant can go from purchase to first draft without help. |
| M9 | **Purchase via Stripe**, including a free test phase. | Test phase: €0 purchase, but address, phone and terms checkbox are mandatory. |
| M10 | **Bring-your-own-key** for daily operation; keys stored encrypted, never shown in the UI. | Key never appears in HTML, logs or mail. |
| M11 | **Publishing via Zernio** to the channels the owner selected. | Approved post appears on the selected channel; the same draft cannot be sent to the same channel twice. |
| M12 | **Every action is logged** in the tenant's log (data-processing agreement). | Log page shows who did what and when. |

### Should have

| ID | Requirement | Acceptance criterion |
|---|---|---|
| S1 | **Onboarding runs on the operator's AI key**; own key only at the end (Client 08.09). | Steps 1–10 work without a customer key. |
| S2 | **The agent proposes, the owner ticks** — audience, topics, tone and colours are suggested, not typed (Client 08.09). | Each of these steps shows ≥ 3 proposals. |
| S3 | **Rules page:** owners edit their own hard rules (e.g. "always use paragraphs") (Client 10.09, from the test evening). | A new rule changes the next draft; an approved constitution is never edited in place — a change creates version + 1. |
| S4 | **Per-channel formats** — each channel gets its own aspect ratio; images are cropped minimally and the owner is told. | Same post renders 1:1 / 4:5 / 1.91:1 correctly. |
| S5 | **Test accounts** (per-account flag, never global) that run fully on the operator's key. | Test account skips the key step and the progress counter shows the shorter total. |
| S6 | **Short greeting** by first name, not by full company string ("'Guten Tag Chris' würde ausreichen"). | Greeting uses the short name. |

### Could have

| ID | Requirement |
|---|---|
| C1 | Photo library (10–20 own photos, optional) used for image posts |
| C2 | LinkedIn PDF carousels in the brand colours |
| C3 | Suggested replies to comments |
| C4 | Paid support coach subscription (€9.99/month) |
| C5 | Push notifications when new proposals are ready |

### Won't have (this release)

| ID | Requirement | Why not |
|---|---|---|
| W1 | Password login | A password is one more thing to forget; magic link + passkey is safer for this user group |
| W2 | Automatic posting without approval | Violates the core promise (M7) |
| W3 | Reach or revenue promises | Legal risk; "story first, message second" |
| W4 | Settings switches for features SAGA does not have | "Switches for missing features would be an interface that lies." |

## 5. Non-functional requirements

| Area | Requirement |
|---|---|
| Privacy | EU hosting; Gemini only with EEA paid terms (inputs not used for training) — confirmed by the owner in onboarding |
| Security | Keys AES-256 encrypted, bound to the tenant ID; rate limiting on login and code entry |
| Usability | Works one-handed on a phone; plain German, "du" or "Sie" as the tenant chooses |
| Reliability | A deploy only happens when all automated gates pass locally *and* on the server |
| Cost | Usage per tenant is recorded (tokens/cost) so the operator can see who consumes what |

## 6. Success measures

- Share of tenants with an **approved constitution** (baseline at 07.10: 2 of 7 → the
  reason the onboarding was simplified in Week 2).
- Drafts that become **published posts** (baseline: 23 drafts, 1 post).
- Time from purchase to first approved draft.

## 7. Risks and assumptions

| Risk | Mitigation |
|---|---|
| Onboarding too long (13 steps, 42 questions) | Short path for test users (Week 2 change) |
| Users share one account by mistake | One account per person; invitations can be mailed to a coordinator but belong to the colleague |
| Corporate mail filters rewrite links | Fallback: 8-character access code (Week 3 bug report) |
| Many users on one AI key | Usage cap per person before scaling beyond ~10 users |
