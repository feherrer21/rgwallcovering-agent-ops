# Problem Statement

**Case:** L2_Case05_Open_Choice_Agent
**Status:** written before any implementation code
**Date:** 2026-08-28

> Personas in this document are synthetic. Two of the seed records describe
> real enquiries; where a real person is behind a record, a stand-in name is
> used here and everywhere else that is published. See
> `02_data_provenance.md`.

---

## 1. Domain and business

RG Wallcovering & Painting, Inc. — wallcovering installation, painting and
interior design, Providence, Rhode Island. Residential and commercial. It is a
small owner-operated business: there is no sales team, no CRM, and no one whose
job is following up on enquiries.

## 2. The user

**Ronald Giraldo, the owner.** Not the website visitor. This distinction is the
whole design.

The certified prototype that precedes this project serves the *visitor*: it
answers questions on the site and hands a written enquiry to Ronald. It stops
there, and that is where the actual cost sits. An enquiry arrives in Ronald's
inbox and then waits on a person who is on a ladder.

Ronald is the user because he is the one who can act on what the system
produces, and the one who is harmed when it is wrong. Every design call in this
project resolves in his favour, including the uncomfortable ones — see
`CLAUDE.md`, "Failure is handled, never swallowed".

## 3. The problem

A captured enquiry is not a qualified enquiry. What arrives is a short prose
summary and a handful of fields, of which most are usually empty, and what
happens next is judgement work done unevenly under time pressure:

- Something is always missing, and it is a *different* something each time.
- The business cannot quote from a vague description. It needs either a site
  visit or detailed information supplied in advance (tier A, owner-confirmed).
  So every lead has to travel from "interested" to one of those two states, and
  the route differs per lead.
- Some enquiries should not be worked by anyone but Ronald.

Today that triage happens in his head, when he has a minute, and it is the step
most likely to be skipped. A follow-up that arrives four days late is a
different business outcome from one that arrives the same evening.

## 4. The decision being delegated

Given one lead — its record, its conversation history, and whatever has already
been attempted — the agent decides **what should happen next**, choosing among:

| Action | Reversible? |
|---|---|
| Ask the lead for the one piece of information that unblocks the rest | Yes (drafted, gated before sending) |
| Check a factual claim against the company corpus | Yes |
| Look at Ronald's calendar and propose a time | Yes (reading) |
| Prepare a follow-up email | Yes (prepared, not sent) |
| **Send that email** | **No — gated** |
| **Book the assessment visit** | **No — gated** |
| Escalate to Ronald with full context | Yes |

The agent is not deciding *whether to pursue* a lead, and it is not scoring
them. It decides the **next action**, one at a time, and it stops at the gate
before anything a customer would see.

## 5. Why an agent — and where I refused to put one

The brief is explicit that choosing an agent where a script would do is an
engineering error. This section is the argument, and it includes the part that
cuts against me.

### 5.1 What the input actually is

Two seed records, both real enquiries, reduced to what matters:

- **Ana** — commercial, office reception, ~300 sq ft, Pawtucket RI. Wants
  design help, has no style in mind. Left an email. No timeline, no budget
  signal.
- **Carmen** (stand-in) — residential, one living-room wall, gives precise
  measurements (3 m × 4 m). No style in mind. **Left a phone number and no
  email**, and the number is a foreign mobile. Wrote in Spanish.

The interesting part is that these two differ on three independent axes at
once: *what is missing*, *which channel exists*, and *what was already promised
to them*.

### 5.2 What was already promised to them

All four seed records contain the same claim: the assessment visit is free
because the customer is nearby, or because they are in Rhode Island. **It is
false.** The owner corrected it on 2026-08-14 — the visit is charged, it costs
the same for everyone, and distance does not enter into it.

So the correct next action for both leads is not a follow-up at all. It is to
notice that the record carries a commitment the business will not honour, and
put that in front of Ronald before anyone contacts them.

### 5.3 The script test

A deterministic version is not hard to imagine, so here it is:

```
if not lead.email:            escalate_to_ronald()
elif not lead.style:          ask_about_style()
elif not lead.timeline:       ask_about_timeline()
else:                         propose_visit()
```

That handles the missing email correctly, and it handles Ana plausibly. It
fails on §5.2, and it fails structurally rather than by accident:

1. **The false promise lives in free prose, not a field.** It appears in three
   different phrasings across four records, one of them in Spanish ("la visita
   de evaluación no tiene costo"). There is no `lead.was_promised_free_visit`
   to branch on. Detecting it means comparing prose against a 370-chunk corpus
   and noticing a contradiction — which is the retrieval-and-judgement step the
   script does not have.
2. **The rules the script encodes are the corpus, and the corpus changes.** The
   free-visit rule was tier-A truth until 2026-08-14 and false afterwards. A
   script hardcodes the business as it was on the day it was written; the
   contradiction it needs to catch is *itself* a rule that moved. The owner is
   the only source in this system that can be wrong and then corrected, and he
   has been, once, already.
3. **"Which question is worth asking" is not an ordering problem.** Ana is
   missing timeline, budget signal, style and a decision-maker. Asking all four
   loses the lead; the fixed priority above asks about style before the fact
   that a commercial reception fit-out has an occupancy date driving
   everything. The right question depends on what the business needs in order
   to quote, which is a corpus fact, not a constant.

The action space is small. The *state* space — free-text history × which
channels exist × which claims were made × what the corpus currently says — is
not, and it is not enumerable in advance.

### 5.4 Where I deliberately did not put the agent

The certified project measured this exact question and the answer went against
agency, so it is recorded here rather than quietly ignored.

There, retrieval started as a tool the model chose to call. Across two runs of
an identical configuration, five of thirty cases changed whether they were
grounded — whether the assistant grounded an answer was a coin flip. Moving
retrieval out of the model's hands and running it every turn left the score
unchanged, held the failures still, and cut input tokens from 64,179 to ~41,000
across the same thirty cases — a 35% saving the owner pays for.

So the line here is drawn deliberately:

- The model decides **whether** a claim needs checking and **what** to look up.
  In this system there is no single incoming message to pre-retrieve on — the
  query depends on which gap the agent is working, which is itself the
  decision. Pre-retrieval has nothing to retrieve *for*.
- The model never decides **how** to retrieve, send, or write to a calendar.
  Those are mechanics.

That is a narrower claim than "the agent decides everything", and it is the one
I can defend with a measurement.

### 5.5 What would falsify this

A deterministic baseline implementing §5.3 runs against the same evaluation set
as the agent. **If the agent's chosen next action agrees with that baseline on
90% or more of leads, the agent is not earning its place**, and that is what
`REFLECTION.md` will say — the brief asks for that finding honestly reported,
and I would rather commit to the threshold now than choose one after seeing the
numbers.

## 6. What success means

Stated now, because a vague definition of success is unscoreable. Measurement
method and the full rubric go in the evaluation doc; these are the criteria.

| | Criterion | Gate |
|---|---|---|
| **S1** | No claim about the business in any prepared or sent output that is not traceable to a tier A/B passage | Zero tolerance |
| **S2** | No irreversible action executes without a recorded human approval | Zero tolerance |
| **S3** | On a lead whose record contradicts the corpus, the agent surfaces the contradiction instead of repeating it | Zero tolerance |
| **S4** | When a required channel is unavailable, the agent reaches a defensible alternative rather than failing silently or inventing one | Measured |
| **S5** | On repeated tool failure, escalation carries the lead, every attempt and every failure reason, within a bounded number of tries | Measured |
| **S6** | Next-action appropriateness against a rubric, compared to the §5.3 baseline | Measured |

S1–S3 are zero-tolerance because each one is a promise a customer would hold
the business to, or an action taken in Ronald's name that he did not authorise.

## 7. Out of scope

- **Talking to visitors.** That is the certified prototype's job and this
  system does not duplicate it.
- **Scoring or ranking leads.** Ronald has tens, not thousands. Prioritisation
  is a problem he does not have.
- **Quoting, or estimating price or duration.** The business does not do this
  without a visit or detailed information, so neither does the agent.
- **Autonomous sending.** Considered and rejected: the gate is the reason
  someone would let this near real work, not a limitation to remove later.
- **Cross-session persistence.** Deferred with a stated reason in
  `03_spec.md`; the memory tier is justified there rather than assumed here.

## 8. Known risks to this framing

- **Two seed leads is not a dataset.** The evaluation set is mostly authored,
  and authored by the same person who wrote the prompt. This is the largest
  threat to every number this project reports. Addressed, not solved, in
  `02_data_provenance.md`.
- **Ronald has not used it.** Every claim about what he needs comes from what
  he told the earlier project, not from watching him work a queue.
- **The agent could be right and useless.** If the correct next action is
  "escalate" for most real leads, the agent is an expensive triage step in
  front of a person who was going to look anyway. §5.5 is the test for that.
