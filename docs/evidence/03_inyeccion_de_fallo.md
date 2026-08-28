# Deliberate failure injection: the planned one did not fire, and why

**Date:** 2026-08-28
**Criterion exercised:** S5 — validate rather than trust, feed the specific
reason back on retry, escalate with full context after repeated failure.

---

## 1. The planned injection was defeated by the agent

`L20` was written with a recipient on `example.invalid` — a reserved TLD that
cannot resolve — specifically so that approving the send would produce a genuine
SMTP rejection rather than a mocked one (`02_data_provenance.md` §2.3).

It never fired. Run against the real model, the agent produced:

```
  cargar {'lead': 'L20', 'canales': 'email (a.kulkarni@example.invalid)'}
  decide escalar_a_ronald — "The lead provided an email address
        (a.kulkarni@example.invalid) which the system indicates has an
        unresolvable domain. This prevents any outbound communication…"
```

It recognised the domain by inspection and escalated without attempting to send.
That is the right behaviour, and it is better than the behaviour the test was
designed to provoke.

**But a failure the model can side-step by looking does not exercise the
recovery path**, and the recovery path is the thing the case asks to be
demonstrated broken on purpose. A designed injection that the system is good
enough to avoid is a finding about the system, not a substitute for the
demonstration.

## 2. The replacement: break the transport, not the data

`INYECTAR_FALLO=correo:n` fails the first *n* send attempts inside
`agente/correo.py`, after validation and after approval — a point the model
cannot inspect its way around, because the failure does not exist until the
action is executed.

Two constraints on how it was written:

- The error text imitates a genuine transient server rejection
  (`421 4.7.0 Temporary System Problem`), because the point is to exercise
  recovery with a reason a model can reason from.
- It is nonetheless **labelled as injected** in the message. A simulated failure
  that passes itself off as real contaminates the evidence, and every trace in
  this repository has to be readable as what it is. A test asserts the label is
  present, and another asserts the switch is off by default.

## 3. The recovery path, end to end

Lead `L04`, real model, `INYECTAR_FALLO=correo:1`:

```
  tool   buscar_corpus({'consulta': 'is the assessment visit charged'}) -> 4 [CCAA]
  decide preparar_correo_visita
  preparar  → cites the owner-confirmed tier A passage
  gate_humano {'decision': 'aprobada', 'quien': 'ronald'}
  FALLO  ejecutar_irreversible: SMTP 421 4.7.0 Temporary System Problem
  recuperar {'herramienta': 'correo', 'gastados': 1, 'restantes': 1}
  decide preparar_correo_visita — "The previous attempt to send the email
         failed due to a temporary SMTP…"
  gate_humano {'decision': 'aprobada'}
  ejecutar_irreversible → email sent to m.webb@example.com
```

Validated rather than trusted, the specific reason fed back, the second attempt
succeeded. Re-approval is required after the retry because the draft is
regenerated: what Ronald authorises is a specific artefact, not a permission
that outlives it.

## 4. The mechanistic failure this exposed

The first run of the same injection produced a correct recovery and a **wrong
explanation**. The agent escalated saying:

> *"This prevented the email from being **prepared for your approval**."*

That is false. The email had been prepared, Ronald had approved it, and the
delivery is what failed. The escalation would have told the owner something that
did not happen — about his own decision.

### Cause

The recovery message read `The `correo` step failed. Reason, verbatim: …`.
"Step" is ambiguous across a pipeline where drafting, approving and sending are
three different stages, and the model resolved the ambiguity wrongly. Nothing in
the message distinguished a failure *before* the gate from one *after* it.

The mechanism is worth naming precisely: **the agent was not wrong about the
world, it was wrong about which stage of its own pipeline it was in**, because
the only evidence available to it was a sentence that did not say.

### Fix

`recuperar` now states the stage explicitly, tells the model when the draft had
already been approved, flags a transient error class as retryable, and closes
with an instruction that follows from the failure mode itself: *do not tell
Ronald something happened that did not*. Measured after the change, the agent's
own account is accurate: *"the previous attempt to send the email failed due to
a temporary SMTP…"*.

## 5. What this says about the retry budget

The budget is spent per tool, per lead, and it counts across sessions through
the ledger — a retry counter that resets when the process restarts is not a
budget, and follow-up is multi-session by nature.

`test_agotar_el_presupuesto_escala_en_vez_de_girar` holds the other end: with a
draft that can never validate, the run escalates with every reason attached
rather than looping, and never reaches the gate with a broken draft. A person
should not be asked to approve something the system already knows cannot be
executed.
