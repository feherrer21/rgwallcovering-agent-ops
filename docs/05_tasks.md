# Tasks

Ordered by `04_plan.md`. A task is done when its check passes, not when the code
is written. `[b]` marks blocked.

---

## Phase 0 — Scaffolding

- [ ] **T0.1** Package layout: `agente/`, `app/`, `eval/`, `tests/`.
      *Check:* `agente/` imports with no Streamlit or HTTP dependency anywhere in
      its tree.
- [ ] **T0.2** `requirements.txt` — `langgraph`, `langchain-openai`,
      `portkey-ai`, `pydantic`, `pydantic-settings`, `numpy`, `fastembed`,
      `python-dotenv`, `pytest`, `pytest-asyncio`, `streamlit`.
- [ ] **T0.3** `agente/config.py` on `pydantic-settings`; every secret from the
      environment, none inline, none logged.
- [ ] **T0.4** `.env.example` with the shape of every required variable and no
      value. *Check:* `.env` is ignored; `.env.example` is committed.
- [ ] **T0.5** `[b]` Resolve the model catalog:
      `curl .../v1/models -H "x-portkey-api-key: $PORTKEY_API_KEY"`.
      *Check:* the cheap and frontier slugs are written into `03_spec.md` §8,
      replacing the model classes.
- [ ] **T0.6** `[b]` `agente/modelo.py` — one client through the gateway.
      *Check:* one round trip returns a completion and the call appears in the
      Portkey dashboard with a cost.

## Phase 1 — Corpus tool

- [ ] **T1.1** Copy the two index files into `data/index/`, recording the source
      commit of the L1 repo in `02_data_provenance.md`.
- [ ] **T1.2** `agente/corpus.py` — fresh reader. Loads, validates alignment and
      the 384 dimension, raises on mismatch rather than guessing.
- [ ] **T1.3** Query embedding with the BGE **query** prefix.
      *Check:* a question whose answer is in a known chunk retrieves that chunk
      above the floor. Crossing the prefix convention degrades everything
      silently, so this check exists to catch exactly that.
- [ ] **T1.4** Relevance floor, per-source cap, empty result as a valid return.
      *Check:* a question the corpus does not cover returns `[]`, and nothing
      downstream treats it as an error.
- [ ] **T1.5** `tier` present on every returned passage or the result is
      rejected. *Check:* a test mutates a chunk to drop `tier` and the loader
      raises.
- [ ] **T1.6** Tool schema for `buscar_corpus`, described so the model can tell
      when *not* to call it.

## Phase 2 — Smallest loop

- [ ] **T2.1** `agente/estado.py` — the dataclasses from `03_spec.md` §3.
- [ ] **T2.2** `agente/grafo.py` — `cargar`, `decidir`, `ejecutar_tool`,
      `escalar`, and the conditional edges out of `decidir`.
- [ ] **T2.3** Prompt for `decidir`: the state, the action space, the tier rules,
      and the instruction that tool output and lead text are data, never
      commands.
- [ ] **T2.4** `agente/traza.py` — step trace to `traces/`: node, action chosen,
      tool in/out, reason.
- [ ] **T2.5** `[b]` Run `L04` and `L11`. *Check:* they take different paths and
      the trace shows the decision, not a branch on a field.

## Phase 3 — Gate and irreversible tools

- [ ] **T3.1** `preparar` writes `accion_propuesta` into state and returns. It
      cannot send.
- [ ] **T3.2** `gate_humano` as a LangGraph interrupt.
- [ ] **T3.3** `ejecutar_irreversible`. *Check:* a test asserts the node has
      exactly one inbound edge in the compiled graph.
- [ ] **T3.4** Approval record — who, when, what, edited or not — written to
      state. *Check:* S2 evidence comes from this record, not from session
      state (`03` §12.1).
- [ ] **T3.5** `agente/correo.py` — SMTP send, new code. Failure propagates; it
      is **not** swallowed the way L1 deliberately swallowed it.
- [ ] **T3.6** `[b]` `agente/calendario.py` — Calendar read and insert.
      *Blocked on the OAuth refresh token.*
- [ ] **T3.7** *Check:* no path reaches a send without approval, including error
      paths and retries. Test enumerates paths rather than asserting one case.

## Phase 4 — Memory

- [ ] **T4.1** `SqliteSaver` checkpointer wired into the compiled graph.
- [ ] **T4.2** Append-only per-lead ledger: what was attempted, when, outcome,
      failure reasons.
- [ ] **T4.3** *Check:* interrupt at the gate, kill the process, resume in a new
      process, complete the approved action. This is the test that earns the
      memory-tier argument in `03` §7.

## Phase 5 — Failure handling

- [ ] **T5.1** Pydantic contract per tool result (`03` §4).
- [ ] **T5.2** `recuperar` injects the specific failure reason into the next
      `decidir` turn. *Check:* the retry prompt contains the actual SMTP code or
      schema mismatch, not a generic message.
- [ ] **T5.3** Retry budget per tool per lead; on exhaustion, `escalar`.
- [ ] **T5.4** Escalation payload: lead, every attempt, every reason in order,
      passages in play. *Check:* a person could act on it without opening a log.
- [ ] **T5.5** Hard cap on model calls per lead (`03` §12.2), so a loop cannot
      drain the allowance.

## Phase 6 — Evaluation and baseline

- [ ] **T6.1** `eval/run.py` over `leads_design.jsonl`, writing per-lead traces
      and a table.
- [ ] **T6.2** `eval/baseline.py` — the four-branch script from `01` §5.3,
      implemented at its strongest rather than strawmanned.
- [ ] **T6.3** `eval/rubric.md` for S1–S6, labelled by a person.
- [ ] **T6.4** Run both on the design set. *Check:* the agreement rate against
      the 90% falsifier in `01` §5.5 is computed and recorded, whatever it says.
- [ ] **T6.5** `[b]` Comparison run on the frontier model. *Check:* cost and
      latency from Portkey, side by side, with S3 called out.

## Phase 7 — Deliberate failure injection

- [ ] **T7.1** SMTP failure via `L20` on the reserved TLD. *Check:* real
      provider rejection, not a mock; retry carries the reason; escalation after
      the budget.
- [ ] **T7.2** `[b]` Calendar failure via `L19`, malformed payload against the
      contract.
- [ ] **T7.3** Capture both in `docs/evidence/` with the traces.

## Phase 8 — Tests

- [ ] **T8.1** `pytest-asyncio` over the loop with tools mocked.
- [ ] **T8.2** Gate invariants from T3.3 and T3.7 as tests, not prose.
- [ ] **T8.3** Recovery path: malformed output → retry with reason → escalation.
- [ ] **T8.4** Capture passing output for the submission.

## Phase 9 — Holdout

- [ ] **T9.1** Run `leads_holdout.jsonl`. **Once.** Nothing tuned afterwards.
- [ ] **T9.2** `docs/07_failure_analysis.md` — every failure, at least two
      explained mechanistically: the input, the output, the cause.

## Phase 10 — Communicate

- [ ] **T10.1** `REFLECTION.md`, 600–1000 words. Failure sections carry the most
      weight. Includes the §5.5 verdict honestly, whichever way it went.
- [ ] **T10.2** Client slide for Ronald. No credentials on it.
- [ ] **T10.3** Demo recording: a normal run and a handled failure.
- [ ] **T10.4** Declared-effort statement from the `PROGRESS.md` log, including
      what was cut and why.

---

## Blocked on someone other than Claude Code

| Task | Needs |
|---|---|
| T0.5, T0.6, T2.5, T6.5 | Portkey API key |
| T3.6, T7.2 | Google Cloud project, Calendar API, OAuth refresh token, and synthetic events seeded in the test calendar |
| T3.5 | Confirmation of the SMTP test mailbox — must not be Ronald's address |
