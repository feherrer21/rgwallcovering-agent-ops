# Failure analysis

Everything this system gets wrong, in one place. The detailed write-ups are in
`docs/evidence/`; this is the index and the argument that connects them.

Eleven evidence notes exist. **Five of them describe defects that were mine
rather than the model's**, and that ratio is the first finding: when an agent
behaves inexplicably, the contract it was handed is the first place to look.

---

## 1. Failures of the agent

### F1 — Over-escalation *(the one that matters)*

**Inputs:** `L16`, `L19` (design set); `L15`, `L07` (holdout).

A gap in what the agent can confirm becomes a handoff to Ronald, even when
enough is confirmable to act.

| Lead | What happened | Expected |
|---|---|---|
| `L16` | An uncovered question about hardwood floors stalled covered wallcovering work | offer the visit |
| `L15` | Same shape: drywall damage the corpus does not mention | offer the visit |
| `L19` | No Tuesday morning free → treated "cannot satisfy exactly" as "cannot decide" | propose a time |
| `L07` | **Clean control.** Escalated because "January" might mean this year or next | offer the visit |

**Mechanism.** The action space forces one choice for the whole lead. An enquiry
that is 80% actionable and 20% unanswerable has no move meaning *"do the 80%,
flag the 20%"*, so the 20% takes the lead.

**Rate:** 2/14 design (cheap model), 3/14 (frontier), 2/6 holdout.

`L07` is the finding that matters. It is the control case, written to detect an
agent that escalates everything, and it caught this one on unseen data. The
over-escalation is not confined to awkward leads.

**Attempted and reverted** — `evidence/05`. A prompt instruction moved three
leads, none to the right answer, broke `L14` which had been correct, and took
unstable leads from 0 to 2. Reverted rather than iterated: fourteen leads is
small enough that further attempts would fit a prompt to fourteen cases.

**Not fixed.** The fix is architectural — a compound action, or an action
carrying open points — and it is named in `REFLECTION.md` as what I would do
differently rather than attempted badly at the end.

### F2 — Query formulation can make S3 unreachable

**Input:** the seed claim *"the assessment visit isn't charged since Pawtucket
is nearby"*. **Detail:** `evidence/00`.

The model searched `"is the assessment visit charged in Pawtucket"`. That
returns one tier C passage; the owner-confirmed tier A passage falls below the
relevance floor. Four of five phrasings retrieve it — the one that fails is the
one the model chose.

**Mechanism.** The corpus holds no document about any town. A place name pulls
the query embedding away from the pricing document. **The failure is silent:** no
error, no empty result, just the wrong passage at a tier that may never be
phrased as company policy.

**Fixed** in the tool contract, not the prompt — it is knowledge about this
corpus. Two regression tests hold it.

### F3 — Fabricated citations

**Detail:** `evidence/09`. The agent cited `chunk_id`s that do not exist —
UUID-shaped inventions where real ones look like `S0-ronald-0000`.

Worse than citing nothing: a draft with no sources is visibly unsupported, one
with invented sources *looks* auditable, and the gate was showing those
identifiers to the approver.

**Cause was mine** (see §2). **Fixed** in two places: the identifier is now shown
to the model, and a validator rejects any cited id absent from the passages
actually retrieved.

### F4 — Tool called from the wrong node after recovery

**Detail:** `evidence/08`. After an injected failure the model called
`redactar_correo` from the decision node, where it is deliberately not bound.

The graph answered rather than crashed and the model corrected itself next turn,
so the system degraded correctly — but it cost a wasted call. The recovery
message says "retry", which the model read as permission to redraft rather than
to decide again.

**Left as observed.** Changing the wording would be tuning after the holdout ran.

---

## 2. Failures that were mine

Listed separately because conflating them with the agent's would misattribute
both.

| | What | Where |
|---|---|---|
| **M1** | A stale claim carried from the L1 provenance note ("service area is tier B only") invalidated `L09`'s label. The agent was right. | `evidence/01` |
| **M2** | `decidir` and `preparar` appended assistant messages containing `tool_call`s with no tool result answering them. **I measured the resulting instability and published it as model non-determinism** before a contract test found the real cause. | `evidence/02` |
| **M3** | The recovery message said "the `correo` step failed" in a pipeline with three stages, so the agent told Ronald an email could not be prepared for approval — when it had been prepared and he had approved it. | `evidence/03` §4 |
| **M4** | The evaluation runner did not save draft bodies, so S1 — a zero-tolerance criterion — could not be scored on its first run. | `evidence/04` §6 |
| **M5** | The model call itself (`decidir`, `agente/grafo.py:85`) had no failure handling. A live gateway rejection (Portkey's per-key $50 policy, exhausted) crashed the deployed app with a raw traceback instead of escalating. Found on `L19`, on the deployed queue, not by design. | `evidence/10` |

**M2 is the one worth dwelling on.** A malformed conversation does not raise, does
not log, and does not fail the same way twice. It degrades behaviour
indistinguishably from an unreliable model, and a plausible supporting finding
existed in the predecessor project. Had I stopped at three runs, this submission
would have carried a documented finding about model variance that was a bug in
its own graph.

---

## 3. What the injection demonstrated, and what it did not

`L20` was written so approving a send would produce a genuine SMTP rejection.
**It never fired**: the agent recognised the unresolvable domain by inspection and
escalated without attempting. Better behaviour than the test wanted, and useless
as a demonstration.

Replaced by breaking the transport at a point that does not exist until the
action executes. The recovered path is in `evidence/03` §3 and `docs/09_demo.md`.

---

## 4. Where I would not trust it

- Any lead where part of the enquiry falls outside the corpus.
- Any clean lead containing a minor ambiguity.
- Any deployment where escalation volume matters, until F1 is fixed
  architecturally.

It will not embarrass the business in front of a customer. It will hand Ronald
work he could have been spared, and he was going to look anyway.
