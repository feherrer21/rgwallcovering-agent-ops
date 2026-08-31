# RG Wallcovering — lead follow-up agent

An agent that works the follow-up queue for **RG Wallcovering & Painting, Inc.**
(Providence, Rhode Island). Given one captured enquiry it decides what should
happen next — ask the question that unblocks the job, offer the assessment
visit, propose a time from the owner's diary, or hand the lead over — and stops
before anything a customer would see.

**The user is Ronald Giraldo, the owner.** Not the website visitor. An enquiry
reaching his inbox is where the cost sits: it then waits on a person who is on
a ladder.

Submission for `L2_Case05_Open_Choice_Agent`.

---

## Start here

If you are evaluating this, three files carry most of it:

| | |
|---|---|
| [`REFLECTION.md`](REFLECTION.md) | What was built, what failed, what I would do differently. 998 words. |
| [`docs/09_demo.md`](docs/09_demo.md) | The demo: a normal run and a failure being handled, as real transcript output. |
| [`docs/07_failure_analysis.md`](docs/07_failure_analysis.md) | Everything it gets wrong, in one place, with mechanisms. |
| [`docs/evidence/`](docs/evidence/) | Ten notes behind that analysis. Four document defects that were mine, not the model's. |

## The headline result, stated plainly

Before building, I committed to a falsifier: a deterministic four-branch script
runs the same evaluation, and **if the agent agrees with it on ≥90% of leads,
the agent did not earn its place.**

| | Design set | Holdout |
|---|---|---|
| Agreement with the baseline | 64% | **33%** |
| Agent correct | 12/14 | 4/6 |
| Baseline correct | **13/14** | 4/6 |

The falsifier did not fire. **But the script scored higher than the agent on the
design set**, and reporting only the agreement number would have been a
comfortable half-truth. What the agent buys over the script is resistance to
injected instructions and a contradiction check that is semantic rather than
lexical — see `REFLECTION.md`.

**Its failure mode is over-escalation**, and it generalises: the holdout escalated
a completely clean lead over a date ambiguous by a year (`evidence/06` §3).

## Where each checklist item lives

**Define**

| Item | Where |
|---|---|
| Problem statement: domain, user, delegated decision | [`docs/01_problem_statement.md`](docs/01_problem_statement.md) §1–§4 |
| Justification that an agent is warranted | [`docs/01`](docs/01_problem_statement.md) §5, with the falsifier in §5.5 |
| Data provenance note | [`docs/02_data_provenance.md`](docs/02_data_provenance.md) |

**Build**

| Item | Where |
|---|---|
| Agent that decides at runtime | [`agente/grafo.py`](agente/grafo.py) — edges out of `decidir` depend on the model's choice |
| At least two tools | Four: corpus and calendar (read-only), email and calendar event (gated) |
| Memory + stated reason | [`agente/persistencia.py`](agente/persistencia.py); the reason is proved by killing the process in [`tests/test_memoria.py`](tests/test_memoria.py) |
| Human validation gate | `gate_humano` as a LangGraph interrupt. `ejecutar_irreversible` has exactly **one** inbound edge, asserted in [`tests/test_gate.py`](tests/test_gate.py) |
| Failure handling | [`agente/validacion.py`](agente/validacion.py), `recuperar` in `grafo.py`, [`agente/escalacion.py`](agente/escalacion.py) |

**Prove**

| Item | Where |
|---|---|
| Evaluation against defined criteria | [`eval/rubric.md`](eval/rubric.md) (written before the first run), results in [`eval/results/`](eval/results/) |
| Cases it gets wrong, ≥2 mechanistic | [`docs/07_failure_analysis.md`](docs/07_failure_analysis.md) — consolidated, with `evidence/00`–`09` behind it |
| Deliberate failure injection | [`evidence/03`](docs/evidence/03_inyeccion_de_fallo.md) — the *planned* one was defeated by the agent and replaced |
| `pytest-asyncio` suite, passing output | [`tests/test_async.py`](tests/test_async.py); captured output in [`evidence/07`](docs/evidence/07_suite_tests.md) |
| Observability evidence | [`evidence/08`](docs/evidence/08_observabilidad.md) — curated traces plus measured cost and latency |

**Communicate**

| Item | Where |
|---|---|
| `REFLECTION.md`, 600–998 words | [`REFLECTION.md`](REFLECTION.md) — 998 |
| One client slide | [`docs/08_client_slide.md`](docs/08_client_slide.md) |
| Demo: normal run + failure handled | [`docs/09_demo.md`](docs/09_demo.md) |
| Declared effort | [`docs/06_effort.md`](docs/06_effort.md) — measured from commit timestamps |

## This is not a continuation of the L1 project

There is a certified L1 submission for the same business
(`rgwallcovering-ai-assistant`). **Its corpus and its captured leads are inputs
here. Its code and its architecture are not**, and the boundary is written down
before any code in [`docs/00_reuse_boundary.md`](docs/00_reuse_boundary.md).

The property L2 scores is that the system decides at runtime. That cannot be
inherited, and wrapping a retrieve-then-answer pipeline in a graph would produce
a cosmetic agent — the specific error the brief's closing note singles out.

## Running it

Requires Python 3.11 and a `.env` (see [`.env.example`](.env.example)). Model
calls route through the company Portkey gateway; there is no personal-API-key
path, by policy.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

.venv/Scripts/python.exe -m scripts.verificar_gateway      # check access, list models
.venv/Scripts/python.exe -m pytest tests/ -q               # 81 tests, no model calls
.venv/Scripts/python.exe -m streamlit run app/main.py      # the queue Ronald uses
```

Evaluation:

```bash
.venv/Scripts/python.exe -m eval.run --set diseno --repeticiones 2
INYECTAR_FALLO=correo:1 .venv/Scripts/python.exe -m eval.run --set diseno
```

`INYECTAR_FALLO` breaks the transport on purpose, after validation and after
approval — a point the model cannot inspect its way around. It is off by
default and a test asserts that.

### Deploying it, and what that costs

It runs at **`rgwallcovering-agent-ops.streamlit.app`** (Streamlit Cloud, free
tier — it sleeps when idle, so open it once before showing it to anyone). The app
is not part of what is graded: the demo deliverable is a transcript
([`docs/09_demo.md`](docs/09_demo.md)), so nothing scored depends on that URL
being up. Three things are worth knowing about deploying it.

`app/main.py` runs both as `python -m streamlit run app/main.py` and when a
platform executes the file directly; it did not always, and the fix is the
`sys.path` insert at the top of the file. All ten variables in
[`.env.example`](.env.example) become secrets in the platform's store, never
committed. Without `APP_PASSWORD` the app refuses to serve at all, deliberately.

Two properties do **not** survive an ephemeral-filesystem host, both named in the
spec before anyone tried:

- **The durable gate.** The checkpoint database and the action ledger are
  discarded on redeploy or sleep, so an approval does not survive a restart —
  the exact property `SqliteSaver` was chosen for, and what evidences S2
  ([`03_spec.md`](docs/03_spec.md) §7.3). It holds locally, where a test proves
  it by killing the process between preparing and approving.
- **Calendar re-authorisation.** The OAuth client is Desktop by design, so the
  deployment performs no consent flow: recovery means re-running
  `scripts/autorizar_calendario.py` on a machine with a browser and updating the
  secret by hand ([`03_spec.md`](docs/03_spec.md) §12.3). Refresh tokens for an
  app left in Testing expire after seven days.

## Layout

```
agente/      the agent. Imports no web framework.
app/         Streamlit UI. Imports agente/, never the reverse.
eval/        runner, deterministic baseline, rubric, the 20-lead set, results
tests/       81 tests, including an async suite and a process-boundary test
scripts/     gateway check, Calendar OAuth, calendar seeding
docs/        specs, evidence, the client slide, the demo
```

## A note on the data

Twenty lead records, committed before any agent code existed. Two derive from
real enquiries and are replaced by synthetic stand-ins **before entering the
pipeline** — real customer data does not belong in a coursework prompt. Every
address is on `example.com` or `example.invalid`; every phone number is in the
`555-01xx` reserved range — **no address the system would send to can reach a
real person**, so a slip during development cannot become a message to a
stranger. (One routable address does appear in a committed evaluation result:
inside the model's own reasoning on `L12`, naming the address it declines to
guess. Left in place rather than redacted — editing evaluation output to tidy a
sentence would be tampering with evidence.)

Six of the twenty were held back and run **once**, at the end, with nothing
tuned afterwards. That commitment, and the one place a fix postdates it, are
documented in [`evidence/09`](docs/evidence/09_citas_inventadas.md) §4.
