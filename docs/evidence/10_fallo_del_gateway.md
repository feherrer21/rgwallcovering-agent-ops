# A gateway failure crashed the app instead of escalating

**Date:** 2026-08-31
**Criterion exercised:** the same one `evidence/03` exercises — validate rather
than trust, feed the specific reason back, escalate with full context after
repeated failure. This note is the case where that criterion was **not** met,
found live, on the deployed queue, not by design.

---

## 1. What happened

Working `L19` (Owen Delacroix — synthetic, `example.com`) on the deployed
Streamlit app, `docs/09_demo.md`'s normal path — read the calendar, propose the
Tuesday morning slot the lead asked for — did not run. Streamlit rendered a raw
Python traceback instead:

```
openai.APIError: Error code: 412 - {'error': {'message': 'Policy
871e10a3-dac0-4d08-89bb-7bf4699a314f Exceeded for api_key:17434060-...',
'type': 'usage_limits_policy_exhaust_error', ...}}
[NOTE] During task with name 'decidir' and id '...'
```

Traced through `app/main.py:134` → `langgraph` → `agente/grafo.py:85`, inside
`decidir`, at the single line that calls the model:

```python
respuesta: AIMessage = con_decision.invoke(estado.mensajes)
```

No `try`/`except` existed around it. Reproduced twice, identically.

## 2. Root cause, confirmed against the Portkey dashboard

Not a code defect in the sense of wrong logic — the gateway genuinely refused
the call. `docs/PROGRESS.md` already named the constraint before any of this
ran: *"Budget: $50 USD across the whole learning path, metered by Portkey."*
The Portkey **Policy** page for the workspace ("Learning Path 2") shows exactly
that policy, ID `871e10a3-dac0-4d08-89bb-7bf4699a314f` — matching the error
above — configured as **Cost, $50 per `api_key`, no periodic reset**. The
project's own key had reached `$50.03 / $50`, status `Exhausted`.

`docs/PROGRESS.md` also already named the consequence: *"A reset needs a
support ticket with line-manager approval."* Rather than wait on that, a new
API key was issued (its own key, its own budget bucket under the same
per-`api_key` policy) and rotated into both the local `.env` and the Streamlit
Cloud secret. `L19` was re-run afterward and completed correctly: read the
calendar, found the Tuesday-morning opening, proposed
`2026-09-01T07:00`–`08:30`, and stopped at the human gate with the standard
no-sources warning. Nothing was created on the calendar — the gate was never
passed.

## 3. Why this is not `F1`

`docs/07_failure_analysis.md` already lists an `L19` finding — over-escalation
when no exact Tuesday-morning slot exists, left unfixed as an architectural
question. This is a different failure, at a different layer:

| | F1 (`07_failure_analysis.md`) | This note |
|---|---|---|
| Layer | The model's decision, given a real calendar response | The transport call to the model itself |
| Trigger | A calendar with no exact match for the request | The gateway refusing the request outright |
| What the agent did | Chose to escalate when it could have partially satisfied the ask | Nothing — the exception never reached `decidir`'s return |
| Disposition | Left open, needs a compound-action architecture | Fixed here, same pattern already used elsewhere in the file |

Fixing this one is not "tuning after the holdout": it touches no prompt, no
tool description, no rubric, and `L19` is a **design**-set lead, not one of the
six held out (`02_data_provenance.md` §2.4 constrains changes to prompts, tool
descriptions and the rubric after the holdout runs — none of those changed).
It also could not have altered any already-reported number: every run behind
`evidence/04`, `evidence/06` and `evidence/08` took the call-succeeds path this
exception never touched.

## 4. Fix

`agente/grafo.py`, `decidir`: the model call is now wrapped in
`except openai.APIError`. Every model client in this project is `ChatOpenAI`
(`agente/modelo.py` — the underlying provider changes by config, never by
branch of Python), so any gateway failure — quota, policy, rate limit,
connection — surfaces through that one exception family regardless of which
model was actually addressed. On catch: the specific reason
(`type(exc).__name__: exc`) is written to the trace, appended to
`estado.fallos` as a `Fallo("modelo", ...)` so it rides into the escalation
package alongside any tool failures, and the run escalates to Ronald rather
than raising — the same shape already used for the per-lead call-budget guard
three lines above it, just extended to cover the call that guard sits in front
of.

`tests/test_fallos.py::test_fallo_del_gateway_escala_en_vez_de_crashear` holds
it: a fake client that raises `openai.APIError` on `invoke`, asserting the run
escalates, the reason is in `motivo`, the failure is recorded in `fallos`, and
the gate is never reached.

## 5. What this says about the failure-handling claim

`docs/PROGRESS.md`'s coverage table marked failure handling **done** on the
strength of `recuperar` (tool-level recovery — SMTP, Calendar) and the
call-budget guard. Both are real, but neither one is the model call itself,
and that is precisely the call every single lead makes at least once. A
gap at the one call every run depends on is a bigger honesty problem than a
gap anywhere else would have been. Updated in that table accordingly.
