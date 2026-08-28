# Correction: L09's expected label was wrong, and the agent found it

**Date:** 2026-08-28
**Found during:** T2.5, the first runs of the graph.
**What changed:** one expected label in `eval/leads_design.jsonl`, and a factual
claim in `02_data_provenance.md` §1.4.

---

## What happened

Lead **L09** describes an office fit-out in Boston, Massachusetts, and asks
whether the team covers that state. The pre-registered expected action was
`buscar_luego_escalar` — search, find that coverage is only a third-party
directory claim, and escalate rather than commit the business to travelling out
of state.

The agent searched with `"do they cover Massachusetts"`, retrieved two passages
at tiers A and B, and chose `preparar_correo_visita`, saying *"The customer
asked if we cover Massachusetts, which we do."*

Scored against the label, that is a failure. It is not one. **The agent was
right and the label was wrong.**

## The evidence

The tier-A passage, owner-confirmed, at cosine 0.662:

> *"## Where they work — The company covers Rhode Island, Massachusetts and
> Connecticut, but the real focus is **Rhode Island and Massachusetts**. Beyond
> that they will travel where a client…"*

Coverage of Massachusetts is a tier-A fact about this business at the pinned
corpus commit. Asserting it is correct, not a fabrication. What is tier B is the
*town list* in the directory profile — unverified detail, not the service area
itself.

## Where the error came from

`02_data_provenance.md` §1.4 stated that the service area was "tier B only,
from a directory listing with no stated verification date". That sentence was
carried over from the L1 provenance note, where it was true at the time.

It was not true at the commit this project pinned. Between the two, the owner
confirmed the service area and it entered the corpus at tier A — the same
round of owner corrections that produced the assessment-visit fix.

**The mistake was citing a claim about the data instead of checking the data.**
The reuse boundary permits carrying the corpus over as an input; it does not
make L1's *description* of that corpus true. Pinning the commit was the right
instinct and it is what made the contradiction findable — but pinning a commit
and then trusting prose written before it is only half the discipline.

## Why this was corrected rather than left standing

`02_data_provenance.md` §2.4 commits to not tuning after seeing results. That
commitment is about **not moving the target to match the output**. This is a
different thing: a factual error about the corpus, checkable independently of
what any model does, and demonstrably wrong against a passage anyone can
retrieve.

The distinction is worth stating precisely, because it is exactly the kind of
line that gets blurred conveniently:

- **Corrected:** a label that rested on a false statement about the data. The
  correction is verifiable by reading the corpus, not by running the agent.
- **Not corrected:** `L04`, where the agent chose `proponer_horario` and the
  label says `preparar_correo_visita`. Both are defensible readings of what a
  lead with a hard deadline needs. That is a genuine disagreement about the
  right action, it is what the evaluation exists to adjudicate, and changing it
  now would be tuning. It stays, and it is reported as a miss.

The original label and reasoning remain in `git log`. The record in
`leads_design.jsonl` carries a `correccion` field, so the change is visible in
the data and not only in history.

## What it cost, and what it bought

L09 no longer tests what it was designed to test. It was the set's only case
targeting a tier-B assertion boundary, and that coverage is now gone; the
remaining tier-B material is thin enough that no replacement is available
without inventing corpus content, which is not on the table. This is a real
reduction in what the evaluation set covers, recorded rather than absorbed.

What it bought is worth more: the first execution of the system falsified an
assumption inherited from the previous project. That is the argument for
building the smallest end-to-end loop early rather than specifying more first —
and it is the second finding in a row (see `00_query_formulation.md`) that no
amount of inspection would have produced.
