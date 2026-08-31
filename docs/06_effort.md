# Declared effort

**Date:** 2026-08-28

The checklist asks for approximate hours and what was cut. Below, what is
**measured** is separated from what is **estimated**, because the predecessor
project recorded a session as 6h26 when it ran 8h49 — a figure written
mid-session and never revised, in the document whose subject was honest
measurement. The separation is the point.

---

## Measured: commit timestamps

Every commit in this repository, first to last, on one day:

| | |
|---|---|
| First commit | 2026-08-28 **09:01** |
| Last commit | 2026-08-28 **20:13** |
| Elapsed span | **11h 12m** |
| Commits | 25 |

Two windows in that span produced no commits, and both were worked:

| Window | Length | What it was |
|---|---|---|
| 11:20 → 12:29 | 1h 09m | Google Cloud console: project, Calendar API, OAuth consent screen, test-user list, credentials. None of it produces a commit. |
| 13:40 → 18:28 | 4h 48m | Confirmed worked by Fabián. The repository holds no artefacts from this window — no commits, no traces. |

**Worked time on 2026-08-28: 11h 12m.**

The second window is stated as attested rather than measured, and the
distinction is kept deliberately. Commit timestamps are evidence; a person's
recollection of their own day is testimony. Both are legitimate, they are not
the same thing, and a reader should be able to tell which is which — that is the
entire reason this document is structured the way it is.

## Estimated: what the repository cannot see

| | Estimate | Basis |
|---|---|---|
| Design conversation before this repo existed | **2–3h** | Produced `RGWallcovering_L2_LeadAgent_HANDOFF.md` — scope, framework choice, tool decisions, the L1/L2 boundary argument. Happened in a separate tool with no timestamps available here. |
| Reading the L1 project to establish what could be reused | included above | Audit of `agente_core/`, the corpus, `leads.jsonl` and the git history |

**Total: ≈ 13h 15m – 14h 15m.**

| | |
|---|---|
| Measured from commits | 6h 24m |
| Attested, no commits in the window | 4h 48m |
| Estimated, predating this repository | 2h – 3h |

Stated as a range because one component is an estimate, not a record.

## Where the time went, by output

Line counts are a poor proxy for effort and are given only to show the shape:

| Area | Lines | Notes |
|---|---|---|
| `docs/` (specs + evidence) | 2,765 | Ten evidence notes, four of which record my own errors |
| `agente/` | 2,469 | Graph, tools, state, validation, persistence, escalation |
| `eval/` | 1,494 | Runner, baseline, label normalisation, rubric, results |
| `tests/` | 1,150 | 81 tests, including the async suite |
| `scripts/` | 433 | Gateway check, OAuth, calendar seeding, process-boundary helper |

The single largest consumer of time was not building. It was **finding and
correcting four defects that looked like model behaviour and were mine**:
malformed conversation history, a stale inherited claim that invalidated a
label, a recovery message that made the agent misreport what happened, and
fabricated citations. Each cost between twenty minutes and an hour, and each is
written up rather than quietly fixed.

## What was cut, and why

Decided in advance in `04_plan.md`, and the order held:

1. **The Streamlit deployment.** The app is written (`app/main.py`) and runs
   locally. The graded demo is a transcript (`09_demo.md`), so nothing scored
   depends on a live URL, and a live free-tier app was a liability in L1 rather
   than an asset.

   ~~It is not deployed.~~ **A deployment was attempted on 2026-08-31**, after
   the submission was otherwise complete and as upside rather than to close a
   gap. It earned its keep by failing: the entrypoint resolved `agente` only
   when launched as `python -m streamlit` from the repository root, so a
   platform that runs the file directly could not import it at all. One
   invocation habit had hidden it for the whole build. Fixed in `809960f`.

   Whether a deployment is live is deliberately **not** claimed here. What is
   recorded is that two properties this spec argues for do not survive an
   ephemeral-filesystem host, both named before the attempt: the durable gate
   (`03_spec.md` §7.3) and the deployment's inability to re-authorise Calendar
   (`03_spec.md` §12.3). Like (2), this is not in the total above — that figure
   is measured from commit timestamps on 2026-08-28.
2. **The Portkey dashboard screenshot.** ~~Cost and latency are computed from
   traces instead.~~ **Supplied after the fact on 2026-08-31** and reconciled
   against the traces in `evidence/08`. It cost about twenty minutes, all of it
   reconciliation rather than capture, and it is *not* in the total above:
   that figure is measured from commit timestamps on 2026-08-28, and reopening
   it for work done three days later would make it mean something else.
3. **A screen recording.** Same reasoning as (1). It would add one thing text
   cannot — a person visibly clicking approve — and that is upside, not a gap.

**Nothing in Prove was cut.** That was the rule set before starting and it held:
the evaluation, the baseline, the holdout, the failure injection and the test
suite are all complete.

## What was not cut but should have been attempted differently

The over-escalation fix. I spent time on a prompt change, measured it worse
(12/14 → 11/14, and 0 → 2 unstable leads), and reverted it. That time was not
wasted — the negative result is in `evidence/05` and it is what identified the
real cause as architectural — but if I had reasoned about the action space
first, I would have reached "this is not a prompt problem" without spending a
run to find out.

## Outstanding

The 2–3h estimate for the design conversation that produced the handoff is the
only figure here still unconfirmed. It is a range rather than a number for that
reason, and the total moves with it.

The 13:40–18:28 window was confirmed as worked by Fabián on 2026-08-28 and the
total reflects that.
