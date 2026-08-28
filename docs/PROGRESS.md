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
| Working agent, decides at runtime | not started | specced in `03` §1–§2 |
| At least two tools | not started | 4 specced in `03` §4 |
| Memory component + stated reason | not started | tier chosen and argued in `03` §7 |
| Human validation gate | not started | specced in `03` §5 |
| Failure handling: validate, retry with reason, escalate | not started | specced in `03` §10 |

### Prove

| Item | Status | Where |
|---|---|---|
| Evaluation against defined criteria | not started | criteria S1–S6 fixed in `01` §6 |
| Cases it gets wrong, ≥2 mechanistic | not started | — |
| Deliberate failure injection | not started | two planned in `03` §10 |
| `pytest-asyncio` suite, passing output | not started | — |
| Observability evidence | not started | two layers planned in `03` §11 |

### Communicate

| Item | Status | Where |
|---|---|---|
| `REFLECTION.md`, 600–1000 words | not started | — |
| One client-facing slide | not started | — |
| Demo: normal run + failure handled | not started | — |
| Declared-effort statement | not started | effort log below |

**Done: 3 of 17.** All three are Define. Nothing in Build, Prove or Communicate
has started.

## Blockers

Ordered by what stops work soonest.

1. **Gemini API key** — needed before any graph run. Free tier, no card.
2. **Portkey API key / workspace** — licensed by the employer. Needed from the
   first run so the cost comparison is measured rather than reconstructed.
3. **Google Cloud project with Calendar API + OAuth refresh token** — requires
   manual authorisation by Fabián; Claude Code cannot do this step. Blocks the
   calendar tool and lead `L19`.
4. **Synthetic events seeded in the test calendar** — without a busy calendar,
   `leer_calendario` has nothing to reason about and the scheduling path is
   untested. Same synthetic-persona discipline as the lead set.

## Open decisions

- **Blind-authored leads.** Offered: Fabián writes 2–3 cases into
  `eval/leads_blind.jsonl` that Claude Code never reads, making part of the
  holdout genuinely blind rather than pre-registered. Recorded as outstanding in
  `02` §2.4. Not taken up yet.
- **SMTP account for the email tool.** Reuse of the L1 test mailbox is assumed
  but not confirmed; it must not be Ronald's address.

## Effort log

Measured from session start, not estimated afterwards. Written as sessions end,
because a number written mid-session and never revised is the exact failure this
file exists to prevent.

| Session | Date | Hours | What |
|---|---|---|---|
| 1 | 2026-08-28 | in progress | Handoff review, L1 reuse audit, repo setup, `CLAUDE.md`, `01`, `02` + 20-lead set, `03` |
