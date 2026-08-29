# The over-escalation fix was measured, made things worse, and was reverted

**Date:** 2026-08-28
**Change attempted:** an instruction in the system prompt separating "something
is unverified" from "something is not yours to decide", and telling the agent
to advance the covered part of an enquiry rather than hand over the whole lead.
**Outcome:** reverted.
**Raw output:** `eval/results/diseno_barato_v1*` (before),
`eval/results/diseno_barato_v2*` (after).

---

## Why the change was made

`evidence/04` measured two misses on the design set, both the same shape:
over-escalation. `L16` stalled a covered wallcovering job over an uncovered
question about hardwood floors; `L19` turned "no Tuesday morning is free" into
"I cannot decide" rather than offering the nearest alternative.

The fix was written as a principle rather than as a patch for two cases — the
distinction between an unverified detail and a decision that is not the
agent's, plus an instruction to ask whether a useful next step exists even with
the uncertainty unresolved.

Tuning against the design set is legitimate. That is what the design/holdout
split exists for: the holdout is the half that must not be tuned against.

## What it measured

| | Before | After |
|---|---|---|
| Correct (with declared alternatives) | **12/14** | 11/14 |
| Strict | 11/14 | 10/14 |
| Agreement with the baseline | 64% | 57% |
| Leads unstable across repetitions | **0** | **2** |

Three leads moved. None of them moved to the right answer.

| Lead | Before | After | Wanted |
|---|---|---|---|
| `L16` | escalate | ask a question | offer the visit |
| `L19` | escalate | offer the visit | propose a time |
| `L14` | **ask a question** | offer the visit | **ask a question** |

`L16` and `L19` stopped escalating, which is what the instruction asked for, and
neither landed on the right action. `L14` was correct before and is wrong now:
it is the lead whose record contradicts itself about scope — one accent wall in
turn one, five rooms in turn four — where asking *is* the useful next step. The
instruction to prefer action pushed it into acting on a scope it had not
resolved.

**One failure was traded for another, and instability was added.**

## Why it was reverted rather than iterated

A one-lead difference on a set of fourteen is not significant; `02` §2.3 said so
before any measurement existed. So the score change alone would not justify
either keeping or reverting.

The instability does. Zero unstable leads became two: the same lead, the same
configuration, different actions on repeated runs. That is a real quality
regression independent of the score, and it points the same way as the
predecessor project's finding — *a metric that moves when nothing changes cannot
be improved against*.

Continuing to iterate was the tempting option and the wrong one. Fourteen leads
is a small enough set that a few more attempts would eventually produce a prompt
that scores well on it, and that prompt would be fitted to fourteen cases rather
than to the problem. The holdout would then measure the fit rather than the
system.

**Reverted. The over-escalation on `L16` and `L19` stands as a known, unfixed
failure**, described mechanistically in `evidence/04` and reported as such.

## What would actually be needed

Not a better sentence in the prompt. The two misses share a mechanism worth
naming: the agent has no way to represent *partial* progress. Its action space
forces one choice for the whole lead, so an enquiry that is 80% actionable and
20% unanswerable has no move that says "do the 80%, flag the 20%".

That is an architecture change — a compound action, or an action that carries a
list of open points alongside it — not a prompt change, and it is beyond what
this build has time for. Recorded in `REFLECTION.md` as what I would do
differently rather than attempted badly now.
