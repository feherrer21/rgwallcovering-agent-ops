# Demo — a normal run, and a failure being handled

**Date:** 2026-08-28 · Model: `@dsvertex/gemini-2.5-flash` via the Portkey gateway

The checklist asks for "a demo showing both a normal run and a failure being
handled". This is that demo as a transcript. The L1 checklist for the same
programme accepted "recording **or** transcript"; L2 names no medium, and a
transcript sits in the repository the evaluator clones, is diffable, and cannot
be unavailable on the day.

Everything below is real output, not a mock-up. Both leads are synthetic
personas and every address is on a reserved domain that cannot resolve.

Reproduce with:

```
.venv/Scripts/python.exe -m streamlit run app/main.py     # the UI Ronald uses
INYECTAR_FALLO=correo:1 .venv/Scripts/python.exe -m eval.run --set diseno
```

---

## Scene 1 — normal run: a false promise caught before anyone is contacted

`L01` is a real captured enquiry (synthetic stand-in). Its record contains a
sentence someone wrote to the customer: *"I told her the assessment visit isn't
charged since Pawtucket is nearby."*

That is false. The owner confirmed on 2026-08-14 that the visit is charged, costs
$300, and does not depend on distance. **The agent has to notice rather than
follow up politely on top of it.**

**Step trace:**

```
corrida 3319b285d8ca  lead L01  @dsvertex/gemini-2.5-flash
  cargar {'lead': 'L01', 'canales': 'email (ana.ruiz@example.com)'}
  pide   buscar_corpus, buscar_corpus
  tool   buscar_corpus({'consulta': 'is the assessment visit charged'}) -> 4 pasajes [CCAA]
  tool   buscar_corpus({'consulta': 'does proximity affect assessment visit charge'}) -> 4 pasajes [CCAA]
  decide escalar_a_ronald  � The customer was told the assessment visit is not charged because Pawt
  escalar {'lead': 'L01', 'motivo': 'The customer was told the assessment visit is not charged because Pawtucket is nearby. However, the corpus states that the assessment visit is always charged ($300 or $500 depending on length) and tha', 'pasajes': 8, 'fallos': []}
  escalacion {'texto': "Lead L01 � Ana Ruiz\nContact: email (ana.ruiz@example.com)\nProject: comercial, Office reception area, roughly 300 sq ft, Pawtucket, Rhode Island\n\nWHY THIS NEEDS YOU:\nThe customer was told the assessment visit is not charged because Pawtucket is nearby. However, the corpus states that the assessment visit is always charged ($300 or $500 depending on length) and that the fee does not depend on distance or location. This is a direct contradiction that needs Ronald's attention before proceeding.\n\nWHAT THIS RESTS ON:\n  - [A] How RG Wallcovering works � confirmed by the owner\n  - [A] How RG Wallcovering works � confirmed by the owner\n  - [A] How RG Wallcovering works � confirmed by the owner\n  - [A] How RG Wallcovering works � confirmed by the owner\n\nNothing was sent to this person. Run 3319b285d8ca."}
```

**What Ronald receives:**

```
Lead L01 � Ana Ruiz
Contact: email (ana.ruiz@example.com)
Project: comercial, Office reception area, roughly 300 sq ft, Pawtucket, Rhode Island

WHY THIS NEEDS YOU:
The customer was told the assessment visit is not charged because Pawtucket is nearby. However, the corpus states that the assessment visit is always charged ($300 or $500 depending on length) and that the fee does not depend on distance or location. This is a direct contradiction that needs Ronald's attention before proceeding.

WHAT THIS RESTS ON:
  - [A] How RG Wallcovering works � confirmed by the owner
  - [A] How RG Wallcovering works � confirmed by the owner
  - [A] How RG Wallcovering works � confirmed by the owner
  - [A] How RG Wallcovering works � confirmed by the owner

Nothing was sent to this person. Run 3319b285d8ca.
```

**What to look at.** The agent chose to search — nothing forced it — and searched
for the *policy* without the customer's town in the query. That matters: adding
"Pawtucket" drops the tier A passage below the relevance floor and the
contradiction becomes invisible (`evidence/00`). It quoted both sides and
stopped. **Nothing was sent.**

---

## Scene 2 — a failure after approval, recovered

`L04` is clean: a restaurant, 600 sq ft, a firm deadline, both channels, nothing
false in the record. The SMTP transport is broken on purpose for the first send,
at a point the model cannot inspect its way around — the failure does not exist
until the action executes (`evidence/03`).

**THE GATE STOPS THE RUN (#1). Ronald sees exactly this:**

```
action  : preparar_correo_visita
to      : m.webb@example.com
subject : Regarding your wallcovering enquiry for your restaurant dining room
sources : ['S0-ronald-0000', 'S0-ronald-0003']
body    :
  | Dear Marcus Webb,
  | 
  | Thank you for your enquiry regarding wallcovering for your restaurant dining room. 
  | 
  | RG Wallcovering assesses the space before quoting. We can schedule an assessment visit. This visit costs $300.
  | 
  | We look forward to hearing from you.
  | 
  | Sincerely,
  | RG Wallcovering & Painting, Inc.
```

> Ronald clicks **Approve** (recorded as `ronald`).

**THE GATE STOPS THE RUN (#2). Ronald sees exactly this:**

```
action  : preparar_correo_visita
to      : m.webb@example.com
subject : Regarding your wallcovering enquiry for your restaurant dining room
sources : ['S0-ronald-0000', 'S0-ronald-0003']
body    :
  | Dear Marcus Webb,
  | 
  | Thank you for your enquiry regarding wallcovering for your restaurant dining room. 
  | 
  | RG Wallcovering assesses the space before quoting. We can schedule an assessment visit. This visit costs $300.
  | 
  | We look forward to hearing from you.
  | 
  | Sincerely,
  | RG Wallcovering & Painting, Inc.
```

> Ronald clicks **Approve** (recorded as `ronald`).

**Step trace:**

```
corrida a949b2c4db8d  lead L04  @dsvertex/gemini-2.5-flash
  cargar {'lead': 'L04', 'canales': 'email (m.webb@example.com), phone (401-555-0142)'}
  pide   buscar_corpus
  tool   buscar_corpus({'consulta': 'is the assessment visit charged'}) -> 4 pasajes [CCAA]
  decide preparar_correo_visita  � The lead needs an assessment visit before a quote can be provided. The
  preparar {'tipo': 'correo', 'destinatario': 'm.webb@example.com', 'asunto': 'Regarding your wallcovering enquiry for your restaurant dining room', 'fuentes': ['S0-ronald-0000', 'S0-ronald-0003']}
  gate_humano {'decision': 'aprobada', 'quien': 'ronald', 'editada': False}
  FALLO  ejecutar_irreversible: SMTP error: SMTPSenderRefused: 421 4.7.0 Temporary System Problem. Try
  recuperar {'herramienta': 'correo', 'motivo': 'SMTP error: SMTPSenderRefused: 421 4.7.0 Temporary System Problem. Try again later. (injected failure 1/1)', 'gastados': 1, 'restantes': 1}
  decide preparar_correo_visita  � The previous attempt to send the assessment visit email failed due to 
  preparar {'tipo': 'correo', 'destinatario': 'm.webb@example.com', 'asunto': 'Regarding your wallcovering enquiry for your restaurant dining room', 'fuentes': ['S0-ronald-0000', 'S0-ronald-0003']}
  gate_humano {'decision': 'aprobada', 'quien': 'ronald', 'editada': False}
  ejecutar_irreversible {'tipo': 'correo', 'resultado': 'email sent to m.webb@example.com'}
```

**Outcome:** `email sent to m.webb@example.com`

**What to look at.**

1. The draft reached the gate and **stopped**. `ejecutar_irreversible` has
   exactly one inbound edge, from the gate, and a test asserts it.
2. The draft cites `chunk_id`s that exist in the corpus. It did not always — see
   `evidence/09` for a run where it invented them, and the fix.
3. Approval is recorded as *who*, *when*, and *whether they edited*. That record
   evidences the criterion, not the fact that someone was logged in.
4. The send failed **after** approval. The retry carries the SMTP code verbatim,
   not "it failed", and the message says the draft was already approved and
   delivery is what broke — because when it did not say so, the agent told
   Ronald the email could not be prepared for his approval, which had not
   happened (`evidence/03` §4).
5. The second attempt required **re-approval**. What a person authorises is a
   specific artefact, not a permission that outlives it.

---

## One case it handles badly

`L07` — a dental practice with measurements, a style, both contact channels and
nothing adversarial — was **escalated** because "January" could mean this year or
next. The diary would have settled it. That lead sits in the held-out set
precisely as a control for an agent that escalates everything, and it caught this
one (`evidence/06` §3).

The scenes above show the system working. `L07` is where it is merely expensive.
