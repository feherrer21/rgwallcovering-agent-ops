# Build Plan

**Case:** L2_Case05_Open_Choice_Agent
**Date:** 2026-08-28

Phases in the order they unblock each other, each with an exit condition that is
checkable rather than declared. The ordering principle: **build the smallest
thing that completes the loop, then add the properties being graded one at a
time**, so that when something breaks it is obvious which addition broke it.

Checklist coverage is tracked in `PROGRESS.md`, not here.

---

## Phase 0 — Scaffolding

Repository layout, dependencies, configuration, and a verified call through the
gateway.

- Package layout: `agente/` (all logic, knows nothing about Streamlit),
  `app/` (the Streamlit front end), `eval/`, `tests/`.
- `config.py` on `pydantic-settings`, secrets from environment only.
- Portkey client per `03_spec.md` §8, and the model catalog resolved with the
  documented `curl` — the setup guide contradicts itself on the Gemini row, so
  the slugs come from the live catalog, not from the guide.

**Exit:** one round trip through the gateway returns a completion, and the
catalog query lists the models §8 will actually name. **Blocked on the Portkey
key.**

## Phase 1 — The corpus tool

A new reader over the inherited index. Written fresh against the documented
schema; no code crosses over (`00_reuse_boundary.md`).

- Load `embeddings.npy` + `chunks.jsonl`, assert alignment and dimension.
- Query embedding with the BGE query prefix — passages were embedded without it,
  and crossing the two silently degrades every similarity in the system.
- Relevance floor, per-source cap, and **empty result is a valid return**.
- `tier` travels intact into the tool result.

**Exit:** given a question the corpus answers, the right passage comes back with
its tier; given one it does not, the result is empty and nothing is invented.
Testable with no model call.

## Phase 2 — The smallest loop that decides

`cargar → decidir → (buscar_corpus | escalar) → fin`. No gate, no email, no
calendar, no memory.

The point is to establish the property being graded before anything is built on
top of it: the model chooses the next action, and the edges out of `decidir` are
conditional on that choice.

**Exit:** two leads from the design set take different paths through the graph,
and the step trace shows why.

## Phase 3 — The gate and the irreversible tools

- `preparar` writes the proposed action into state; it does not act.
- `gate_humano` interrupts; a person approves, edits or rejects.
- `ejecutar_irreversible` is the only node that sends, with exactly one inbound
  edge.
- The approval record — who, when, what, edited or not — is written to state.

**Exit:** a test asserts the single inbound edge, and a second test asserts no
send occurs on any path where approval is absent, including error paths.

## Phase 4 — Memory

- `SqliteSaver` checkpointer, so approval survives a process restart.
- Append-only per-lead action ledger.

**Exit:** a run is interrupted at the gate, the process is killed, a new process
resumes from the checkpoint and completes the approved action. This is the test
that justifies the tier choice in `03_spec.md` §7 — without it, the reasoning is
just an argument.

## Phase 5 — Failure handling

- Typed validation contract on every tool result (`03` §4).
- `recuperar` injects the specific failure reason into the next `decidir` turn.
- Retry budget, then `escalar` with the lead, every attempt and every reason.

**Exit:** an injected malformed tool result produces a retry whose prompt
contains the actual reason, and exhausting the budget escalates rather than
loops.

## Phase 6 — Evaluation harness and the deterministic baseline

- Runner over `eval/leads_design.jsonl`, writing per-lead traces and a table.
- The four-branch baseline from `01_problem_statement.md` §5.3, implemented
  honestly rather than strawmanned.
- Rubric for S1–S6, labelled by a person against the runner's output.

**Exit:** design set measured for both agent and baseline, with the agreement
rate that §5.5 committed to as a falsifier.

## Phase 7 — Deliberate failure injection

Both planned against real data rather than invented (`03` §10):

- SMTP — `L20`, on a reserved TLD, so the rejection is a genuine provider error.
- Calendar — `L19`, the only lead requesting a specific time, with a malformed
  payload against the contract.

**Exit:** both recoveries captured in traces, with the retry reason and the
escalation contents visible.

## Phase 8 — The test suite

`pytest-asyncio` over the agent loop, with tools mocked, covering the recovery
path and the gate invariants from Phase 3.

**Exit:** passing output captured for the submission.

## Phase 9 — Holdout, once

Run `eval/leads_holdout.jsonl`. **Once.**

Nothing is tuned afterwards. If it exposes a failure, the failure is reported
and explained mechanistically; it is not fixed and re-measured. That commitment
is what makes the number mean anything (`02_data_provenance.md` §2.4).

**Exit:** holdout results recorded, and at least two failures explained by
mechanism rather than attributed to model imperfection.

## Phase 10 — Communicate

`REFLECTION.md` (600–1000 words, failure sections carry the most weight), the
client slide, the demo recording of a normal run and a handled failure, and the
declared-effort statement from the log in `PROGRESS.md`.

---

## Ordering constraints

- Phase 0 blocks everything. There is no local fallback to develop against,
  because policy removes it (`03` §8).
- Phases 3 and 4 are inseparable in practice: the gate is what makes durable
  memory necessary, and durable memory is what makes the gate testable.
- Phase 6 must precede Phase 7. Measuring the happy path after breaking things
  deliberately confuses two different sources of failure.
- Phase 9 must follow everything. Running it earlier destroys the only property
  the holdout has.

## What gets cut first if time runs short

Recorded now, so the trade-off is a decision rather than a drift:

1. **The Streamlit deployment.** The graded demo is a recording (`03` §12.3), so
   a local run with Ronald over a screen share loses nothing that is scored.
2. **The calendar tool.** Two tools are required and the corpus and email tools
   already satisfy that. `L19` would move from a calendar failure to a second
   validation failure on the email path.
3. **The Opus comparison run.** Painful, because it is cheap evidence, but the
   agent stands on the cheap model alone if it must.

Nothing in Prove gets cut. That is where the marks are.
