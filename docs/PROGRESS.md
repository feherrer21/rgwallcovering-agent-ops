# PROGRESS

Updated as work happens, not at phase boundaries. The coverage table is the
honest answer to "how much is left", because it is what is actually graded.

**Last updated:** 2026-08-28

---

## Where this stands

Specs are committed and pushed; no implementation code exists yet. That
ordering is deliberate and is itself evidence — `git log` shows the problem
statement, the evaluation data and the architecture landing before any agent
code.

| Commit | What landed |
|---|---|
| `dadd3b2` | Repo rules, reuse boundary, `.gitignore` |
| `2a86e30` | `CLAUDE.md` — standing context |
| `f736789` | `01_problem_statement.md` |
| `8a904a9` | `02_data_provenance.md` + the 20-lead evaluation set |
| `6dce51c` | `03_spec.md` — the graph |
| `a1d2ae4` | Model routing corrected against Perficient policy |
| `902f772` | Deployment and access control |
| `26eb169` | `04_plan.md` + `05_tasks.md` |
| `d332678` | Scaffolding — `agente/`, `config.py`, `.env.example` |
| `ffc097d` | Phase 1: the corpus tool, 19 tests passing |
| `2f00953` | Catalog check script |
| `6c9041e` | Gateway live, models resolved, first measured finding |
| `1fdedb7` | SMTP inherited and verified; Calendar authorisation script |
| `e3a4930` | Why the Calendar client is Desktop |
| `eb69eac` | Calendar authorised, dedicated calendar seeded |
| `024539b` | Phase 2: the loop decides |
| `b30cf90` | Phase 3: the human gate |
| `32f6309` | Phase 4: durable memory |
| `5ce2485` | Phase 5: failure handling |
| `626606d` | Phase 6 + 8: evaluation, baseline, async suite |
| `96cb39f` | Phase 9: holdout run, and a reverted prompt fix |
| `7ab412d` | REFLECTION.md, client slide, the Streamlit queue |
| `f9187a6` | Captured test output, curated traces |
| `e98f9d8` | Fabricated citations found and fixed; demo transcript |
| `cfad700` | Declared-effort statement |
| `16654c3` | Effort total confirmed at 13h15–14h15 |
| `7bfd380` | README |
| _this_ | Final review: consolidated failure analysis, three corrections |

## Submission checklist coverage

Status is against the real checklist, not against phases.

### Define

| Item | Status | Where |
|---|---|---|
| Problem statement: domain, user, delegated decision | **done** | `01` §1–§4 |
| Justification an agent is warranted | **done** | `01` §5, incl. the falsifier in §5.5 |
| Data provenance note | **done** | `02` |

### Build

| Item | Status | Where |
|---|---|---|
| Working agent, decides at runtime | **loop working** | `agente/grafo.py`; different leads take different paths, driven by the model |
| At least two tools | **4 of 4 built** | `buscar_corpus`, `leer_calendario` (read); `enviar_correo`, `crear_evento` (gated). All exercised against the real services |
| Memory component + stated reason | **done** | `SqliteSaver` + per-lead ledger, with the reason argued in `03` §7 and *proved* by killing the process between preparing and approving |
| Human validation gate | **done** | `gate_humano` as a LangGraph interrupt; one inbound edge to the send node, asserted by test |
| Failure handling: validate, retry with reason, escalate | **done** | typed contracts before the gate, `recuperar` feeding the verbatim reason back, budget per tool per lead counted across sessions, escalation carrying every attempt |

### Prove

| Item | Status | Where |
|---|---|---|
| Evaluation against defined criteria | **done** | `evidence/04` (design, 12/14) and `evidence/06` (holdout, 4/6). Agreement with the baseline: 64% design, **33% holdout** — the falsifier is further from firing on unseen data |
| Cases it gets wrong, ≥2 mechanistic | **done** | Over-escalation explained mechanistically and shown to generalise to unseen leads including a clean control (`evidence/04`, `06`); plus `00`, `02`, `03`, and a fix that was measured and reverted (`05`) |
| Deliberate failure injection | **done** | `INYECTAR_FALLO`; the planned one was defeated by the agent and replaced — `evidence/03` |
| `pytest-asyncio` suite, passing output | **done** | `tests/test_async.py`, 7 async tests over the loop, tool mocking and the recovery path |
| Observability evidence | **done** | `evidence/08` — two curated traces plus measured cost and latency. A Portkey dashboard screenshot is optional upside |

### Communicate

| Item | Status | Where |
|---|---|---|
| `REFLECTION.md`, 600–1000 words | **done** | 1000 words. The failure sections are the longest, including three failures that were mine |
| One client-facing slide | **done** | `docs/08_client_slide.md`. No credentials anywhere on it |
| Demo: normal run + failure handled | **done** | `docs/09_demo.md`, a transcript of both scenes. L2 names no medium and L1 accepted "recording or transcript"; a recording is optional upside |
| Declared-effort statement | **done** | `docs/06_effort.md`. Measured from commit timestamps, with the two gaps named and one flagged for Fabián to confirm |

**Done: 17 of 17.** Every checklist item is authored and the effort total is confirmed at
13h15–14h15. Optional upside, required by no checklist wording: a Portkey
dashboard screenshot, and a screen recording of the gate being clicked.  The decision loop runs end to
end on real leads: `L01` and `L02` detect the false free-visit promise, quote
both sides and escalate — on the cheap model. Two findings are recorded in
`docs/evidence/`, and the second one corrected a mistake of mine rather than
the agent's.

## Blockers

Ordered by what stops work soonest.

None blocking. Everything the build needs is in place: the gateway is live with
both models resolved, SMTP authenticates, and Calendar is authorised against a
**dedicated** calendar seeded with a synthetic agenda.

Two dated reminders rather than blockers:

1. **Re-authorise Calendar before any demo.** The consent screen is in Testing,
   where Google expires refresh tokens after seven days. One command:
   `scripts/autorizar_calendario.py`. A token minted weeks earlier and assumed
   to work is how a working system looks broken in front of a client.
2. **`primary` is off limits, permanently.** It holds real appointments, six of
   them with real third-party attendees who never consented to their details
   passing through an AI gateway. The agent reads only the dedicated calendar.

**Budget:** $50 USD across the whole learning path, metered by Portkey. A reset
needs a support ticket with line-manager approval, so iteration runs on the
cheapest capable model and the frontier model is spent on the comparison run
only.

## Open decisions

- **Blind-authored leads — offered, not taken up.** Fabián writing 2–3 cases
  that Claude Code never reads would make part of the holdout genuinely blind
  rather than pre-registered. No such file exists; the offer stands and is
  recorded as outstanding in `02` §2.4 rather than quietly dropped.
- **SMTP account for the email tool.** Reuse of the L1 test mailbox is assumed
  but not confirmed; it must not be Ronald's address.
(none blocking.)

## Closed since the handoff

- **The gateway key in the hosting secret store** — decided: same mechanism the
  L1 deployment used and the same one the setup guide recommends over committing
  a `.env`. The guide also permits personal accounts for learning-path purposes,
  drawing its prohibition at Perficient codebases and Perficient clients, and
  this is neither. The difference from L1 is whose credential it is, which the
  safeguards already specified cover: access control on the app, rate limiting
  from the first deploy, a hard cap on model calls per lead, and a $50 ceiling
  that bounds the worst case by construction. A scoped virtual key is preferred
  if the workspace offers one.
- **How the human gate is protected in the UI** — answered in `03` §12: an
  access-control secret in the platform store, kept structurally separate from
  the approval record that actually evidences S2.
- **Which model, via Portkey** — answered in `03` §8, and the choice turned out
  to be constrained by policy rather than free.
- **Local project location and repo name** — `rgwallcovering-agent-ops`, its own
  git history, pushed to a separate GitHub repository.
- **Adversarial lead design and what is held back** — `02` §2.2–§2.4.

## Effort log

Measured from session start, not estimated afterwards. Written as sessions end,
because a number written mid-session and never revised is the exact failure this
file exists to prevent.

Superseded by `docs/06_effort.md`, which measures from commit timestamps rather
than from memory. Summary: 11h12 worked on 2026-08-28 — 6h24 measured from
commits, 4h48 attested — plus 2–3h of design conversation predating this
repository. Total ≈13h15–14h15.
