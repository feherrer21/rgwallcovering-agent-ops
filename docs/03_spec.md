# Architecture Spec

**Case:** L2_Case05_Open_Choice_Agent
**Status:** written before any implementation code
**Date:** 2026-08-28

Specifies the graph before it is built: nodes, state, tools, where the human
gate sits, which memory tier and why, model routing, failure handling and
observability. Decisions that were rejected are recorded with their reason.

---

## 1. Shape of the system

One lead at a time. The agent is given a lead record and decides what should
happen next, repeatedly, until it either reaches an action that requires a
human or concludes there is nothing to do.

```
                 ┌──────────┐
                 │  cargar  │  (determinista)
                 └────┬─────┘
                      ▼
      ┌────────► ┌──────────┐ ─────────────────► escalar ──► FIN
      │          │ decidir  │                        ▲
      │          └────┬─────┘ ──► preparar ──┐       │
      │               │                       │       │
      │          ejecutar_tool                ▼       │
      │               │                 gate_humano   │
      │               ▼                  (interrupt)  │
      │          ┌──────────┐                 │       │
      └───────── │ validar  │ ──── fallo ──► recuperar┘
                 └──────────┘                 │
                                        aprobada
                                              ▼
                                    ejecutar_irreversible
                                              │
                                              ▼
                                          validar ──► FIN
```

`decidir` is the only node that calls the model for a routing decision. Every
edge leaving it is conditional on what the model chose, not on a step counter.

## 2. Nodes

| Node | Kind | What it does |
|---|---|---|
| `cargar` | deterministic | Lead record and prior conversation into typed state. No model call. |
| `decidir` | **model** | Given the state, chooses the next action: search the corpus, read the calendar, prepare an irreversible action, or escalate. This is the agentic step. |
| `ejecutar_tool` | deterministic | Dispatches the chosen read-only tool. Mechanics only. |
| `validar` | deterministic | Checks tool output against its contract. Output never reaches the model unvalidated. |
| `preparar` | **model** | Drafts the irreversible action — email body, or event details — as *state*, not as an effect. |
| `gate_humano` | **interrupt** | Graph halts. A person sees exactly what would happen and approves, edits or rejects. |
| `ejecutar_irreversible` | deterministic | The only node that sends email or writes to the calendar. Reachable from `gate_humano` alone. |
| `recuperar` | deterministic | Feeds the *specific* failure reason back into the next `decidir` turn, within a retry budget. |
| `escalar` | deterministic | Builds the full-context handoff to Ronald and ends the run. |

## 3. State

```python
@dataclass
class EstadoLead:
    lead: RegistroLead                 # el registro capturado
    turnos: list[Turno]                # la conversación original con el visitante
    acciones_previas: list[Accion]     # lo ya intentado sobre este lead
    hallazgos: list[Pasaje]            # pasajes recuperados, con su tier
    contradicciones: list[Contradiccion]  # afirmaciones del registro que chocan con el corpus
    accion_propuesta: Accion | None    # preparada, esperando el gate
    aprobacion: Aprobacion             # pendiente | aprobada | editada | rechazada
    intentos: dict[str, int]           # presupuesto de reintentos por herramienta
    fallos: list[Fallo]                # motivo específico de cada fallo, en orden
    escalacion: Escalacion | None
```

`hallazgos` carries `tier` per passage from the index all the way into the
prompt. Dropping it silently breaks S1, so it is part of the type, not a
convention.

`fallos` accumulates rather than overwrites. The escalation needs every reason,
not the last one.

## 4. Tools

Four, split by whether the world changes.

### 4.1 Read-only — the model calls these directly

| Tool | Contract | Validated on |
|---|---|---|
| `buscar_corpus(consulta: str)` | Returns passages with `tier`, or an empty list | Empty is a valid result, not an error. Every passage has a known tier or the result is rejected. |
| `leer_calendario(desde, hasta)` | Returns busy intervals | Parseable datetimes, `desde < hasta`, no interval longer than the queried window |

Retrieval is a decision here, and `01_problem_statement.md` §5.4 explains why
that reverses a measured finding from L1: there is no single incoming message to
pre-retrieve on, because the query depends on which gap the agent is working.

### 4.2 Irreversible — the model *proposes*, it does not call

| Tool | Contract |
|---|---|
| `enviar_correo(destinatario, asunto, cuerpo)` | Recipient parseable and routable, body non-empty, no unsourced business claim |
| `crear_evento(inicio, fin, titulo, descripcion)` | Slot free per the last calendar read, within business hours, duration bounded |

**This is the architectural expression of the gate.** For these two, the model's
tool call is a *proposal written into state*. Execution is a separate graph
transition that only `gate_humano` can authorise. There is no code path where a
model output reaches SMTP or the Calendar API directly — not on the happy path,
not on a retry, not in an error handler.

## 5. The human gate

Implemented as a LangGraph interrupt before `ejecutar_irreversible`. The graph
stops, the state is checkpointed, and the run resumes only when a person
resolves the interrupt.

What the person sees: the exact recipient, subject and body, or the exact event;
the lead it belongs to; the passages the claims rest on with their tiers; and
any contradiction found in §6. Approve, edit-then-approve, or reject with a
reason — the reason returns to `decidir` as input.

Three properties this must have, and they are testable:

1. **Structural, not procedural.** `ejecutar_irreversible` has exactly one
   inbound edge. A test asserts that.
2. **Survives a restart.** Approval may arrive minutes later, after a refresh.
   This drives the memory decision in §7.
3. **Rejection is information.** A rejected action feeds its reason back rather
   than ending the run silently.

## 6. Contradiction check

The one piece of domain logic that is not generic agent plumbing, and the
reason this problem is not a script (`01` §5.3).

Before any outbound action is prepared, `decidir` is expected to check claims
made to the lead in the captured conversation against the corpus. Where a claim
in the record contradicts a tier-A passage, the contradiction is recorded in
state and the run escalates instead of following up.

The live case: all four real seed enquiries were told the assessment visit was
free. The corpus says it is charged, identically, regardless of distance. Three
phrasings of that claim are in the evaluation set, one of them never using the
word "visit" (`02_data_provenance.md` §2.3).

This is a **model** judgement, not a keyword match, and the held-out `L03`
exists to catch the keyword shortcut if it is taken.

## 7. Memory — the tier, and why

Two different needs, deliberately not solved by one mechanism.

### 7.1 Run state — durable checkpointer (`SqliteSaver`)

**Chosen over an in-process checkpointer because of the gate.** The graph halts
at `gate_humano` and waits on a human. If run state lives only in process
memory, an approval that arrives after a restart resurrects nothing: the
prepared action is lost, and a prepared-action-silently-lost is precisely the
failure the gate exists to prevent. A durable checkpointer makes approval a
resumable transition rather than a race against the process lifetime.

Rejected: in-memory (`MemorySaver`) — simpler, and wrong for the reason above.
Rejected: Postgres — correct at a scale this does not have (see `CLAUDE.md`,
"build for the size this actually is").

### 7.2 Per-lead history — append-only action ledger

What was attempted on this lead, when, with what outcome, and every failure
reason. Append-only JSONL keyed by `lead_id`.

Separate from the checkpointer because it has a different lifetime and a
different reader. Follow-up is inherently multi-session — an email goes out
Monday, a reply arrives Wednesday — and "escalate after repeated failure" is
meaningless if repetition is only counted within one process. Ronald also needs
to read this; a checkpointer blob is not for human eyes.

### 7.3 Production gap, named now

Ephemeral-filesystem hosting (Streamlit Community Cloud and most free PaaS
tiers) discards both on redeploy. Shipping this to a live queue without a
mounted volume or a managed database would silently lose the record of what was
already sent to a customer. **Recorded here rather than discovered later.**

## 8. Model routing

| | Choice |
|---|---|
| Gateway | **Portkey**, all calls, from the first day of building — not only for the final runs. Licensed by the employer, so log volume is not a constraint. |
| Build and iterate | **Gemini 2.5 Flash** (free tier). Iteration is where spend accumulates: dozens of debugging runs of the graph. |
| Cheap paths | **Gemini 2.5 Flash-Lite** — higher daily quota, used for the deterministic baseline and low-stakes validation. |
| Final comparison | One evaluation run on **Claude Opus 5** against the same set, reported side by side with Flash on cost, latency and criteria. |

The comparison is not a luxury: it satisfies "route model calls through Portkey
so cost and latency are observable", "justify the framework choice against at
least one alternative you rejected", and the evidence standard's demand for a
measured number — with one run.

**The interesting outcome is S3.** Detecting that free prose contradicts a
tier-A passage is the hardest thing asked of the model. If Flash fails it and
Opus passes, the finding is a measured architectural result — possibly "Flash
everywhere except the contradiction check". If Flash passes, the work was done
for free and that is the business-impact line in the reflection. Both outcomes
are reportable; neither is assumed.

**Production gap, named now:** the Gemini free tier permits the provider to use
prompts and outputs for product and model improvement, including human review.
That is why synthetic substitution is enforced at the data layer
(`02_data_provenance.md` §3.2) rather than at publication. Real customer leads
require a paid tier before this system processes a single one.

## 9. Framework choice, and what was rejected

**LangGraph.** The deciding factor is the gate, not the graph. A first-class
interrupt with a durable checkpointer means approve-later is a supported
transition rather than hand-rolled state.

**Rejected — a plain provider tool-use loop.** This is what the L1 project used
and it works well; the cost of adopting it here is that pausing for human
approval, checkpointing the paused state, and resuming it are all mine to build
and to prove correct. That is exactly the surface the case is scoring, so
building it by hand would be spending the effort where it is least defensible.

**Rejected — n8n.** A visual workflow fits a fixed sequence. The decomposition
here is a decision loop with a retry budget and typed validation contracts,
which is code. The required evidence — a `pytest-asyncio` suite over the loop
with tool mocking — is also markedly easier from Python.

**Rejected — multi-agent / supervisor decomposition.** One decision-maker, four
tools, tens of leads. A supervisor over specialised sub-agents would be
speculative generality, and `CLAUDE.md` says to treat that as a signal rather
than as thoroughness.

## 10. Failure handling

1. **Validate, do not trust.** Every tool result passes a typed contract (§4)
   before it can enter state or reach the model.
2. **Retry carries the reason.** `recuperar` injects the specific validation
   error or provider error into the next `decidir` turn — the schema mismatch,
   the SMTP code and text, the malformed datetime. Not "it failed".
3. **Bounded, then escalate.** Two retries per tool per lead. On exhaustion,
   `escalar` hands Ronald the lead, every action attempted, every failure reason
   in order, and the passages in play. Never an unbounded loop.

Deliberate injection, planned against real data rather than invented:

- **SMTP** — `L20` uses `example.invalid`, a reserved TLD guaranteed never to
  resolve, so the rejection is a genuine provider error and not a mock.
- **Calendar** — `L19` is the only lead that requests a specific time, so it is
  where a malformed payload is injected to exercise the validation contract.

## 11. Observability

Two layers, because neither is sufficient alone.

- **Portkey** — per-call cost, latency, tokens, model. Answers "what did this
  cost and how slow was it", and carries the Flash/Opus comparison.
- **Local step trace** (`traces/`, gitignored) — node transitions, the action
  chosen and why, tool inputs and outputs, validation verdicts, retry reasons,
  gate decisions. Portkey sees model calls; it does not see that `validar`
  rejected a payload or that a human edited a draft before approving.

Evidence that ships is curated by hand into `docs/evidence/` with synthetic
personas, because raw traces contain conversation content.

## 12. Out of scope for this spec

Streaming, multi-tenant support, a queue runner over many leads at once, an
inbound-reply parser, and any abstraction over the model provider beyond what
Portkey already gives in configuration.
