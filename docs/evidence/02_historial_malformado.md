# Finding: an unanswered tool call made the drafting node fail intermittently

**Date:** 2026-08-28
**Found during:** T3.x, the first end-to-end run of `L19` through the gate.
**What is here:** a bug with a mechanism, fixed twice because the first fix was
incomplete — and a conclusion I published and then had to withdraw.

---

## 1. The bug

`L19` reached the gate correctly on the first run: the agent read the calendar,
found no Tuesday morning free, said so, and proposed Tuesday afternoon. The
second run of the same lead produced this trace:

```
  pide   leer_calendario
  tool   leer_calendario({'dias': 30, 'duracion_horas': 1.5}) -> 0 pasajes [-]
  decide proponer_horario  — "no Tuesday morning slots are available…"
  FALLO  preparar: el modelo no llamó a la herramienta de redacción
  FALLO  decidir: respuesta sin tool_call
  FALLO  preparar: el modelo no llamó a la herramienta de redacción
  decide preparar_correo_pregunta
```

It decided correctly, then failed three times to draft anything, then fell back
to a different action and drafted an email instead.

### The mechanism

When the model called `proponer_siguiente_accion`, `decidir` recorded the
decision and appended the assistant message to the conversation — **without
appending a `ToolMessage` answering that tool call.**

The result is a malformed history: an assistant turn containing `tool_calls`
with no corresponding tool result. That is not a valid conversation under the
OpenAI-compatible wire format the gateway speaks, and the provider's response
to it is unspecified. Empirically it tolerated the shape in one run and not in
the next.

The failure surfaced two nodes away from its cause. `decidir` looked fine —
it decided, and the decision was right. `preparar` looked broken, and it was
not: it was being handed an invalid conversation.

### The fix

`decidir` now appends a `ToolMessage` acknowledging the decision call
(`agente/grafo.py`). Well-formedness is not decoration here; it is the contract
the provider is entitled to.

Measured after the fix, over three runs: drafting failures dropped from three in
one run to zero or one.

## 2. The first fix was incomplete, and I drew the wrong conclusion from it

After acknowledging the decision call, three runs of `L19` gave this:

| Run | Action chosen |
|---|---|
| 1 | `proponer_horario` |
| 2 | `escalar_a_ronald` |
| 3 | `escalar_a_ronald` |

I wrote this up as model non-determinism — the same coin-flip phenomenon L1
measured, reappearing where it could not be designed away because choosing the
action *is* the product. That conclusion was wrong, and it was wrong in the
direction that would have been comfortable: it attributed my instability to the
model.

A regression test asserting that every `tool_call` in the final history has a
matching response caught the actual cause. The fix had been applied to
`decidir` and **not** to `preparar`, which was leaving its own drafting call
unanswered. That matters specifically on the rejection path, where control
returns to `decidir` carrying the malformed history forward.

With both nodes acknowledging their calls, four runs of `L19`:

| Run | Action chosen | Internal retries | Model calls |
|---|---|---|---|
| 1 | `proponer_horario` | 2 | 4 |
| 2 | `proponer_horario` | 0 | 3 |
| 3 | `proponer_horario` | 0 | 2 |
| 4 | `proponer_horario` | 3 | 6 |

**Four out of four, matching the pre-registered label.** The chosen action is
stable; what still varies is how many internal retries it takes to get there,
which costs tokens and is worth watching but is not a correctness problem.

### What this is worth knowing

The instability was mine. A malformed conversation does not raise, does not log,
and does not fail the same way twice — it degrades a model's behaviour in a way
that is indistinguishable from the model being unreliable. Had I stopped at the
first fix and the first three runs, this project would have carried a documented
"finding" about model variance that was really a bug in its own graph, and it
would have been a plausible one, because a comparable finding exists in the
predecessor project.

The test is what separated the two, and it was written to check a contract
rather than an outcome.

### What still stands for Phase 6

The commitments below are kept, on their own merits rather than on this
evidence:

- Run the design set more than once per configuration, and report run-to-run
  disagreement as a number.
- Treat a lead whose action changes between identical runs as an unstable case
  in its own right.
- Before attributing variance to the model, check the conversation is
  well-formed. That is now a cheap check and it has already been wrong once.

## 3. A design decision that paid off by accident

Approving the gate during this run sent a **real** email over SMTP, to
`o.delacroix@example.com`. It reached nobody, because every address in the
evaluation set is on `example.com` or `example.invalid` — reserved domains that
cannot resolve (`02_data_provenance.md` §3.2).

That constraint was written as a privacy measure. It also turned out to be the
thing that made it safe to exercise the irreversible path for real during
development, which is not a small property for a system whose main risk is
sending something to a customer by mistake.
