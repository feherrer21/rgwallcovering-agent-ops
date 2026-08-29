# Finding: the agent cited sources that do not exist

**Date:** 2026-08-28
**Found during:** producing the demo transcript, after the holdout had run.
**Criterion at risk:** S1 — no claim about the business that is not traceable.
**Disclosure:** this fix **postdates the holdout run**. See §4.

---

## 1. What was found

The drafting tool asks the model for `chunk_ids` — the identifiers of the
passages each claim rests on — so that a person approving a draft can check what
it is built from. A run produced this at the gate:

```
  to      : m.webb@example.com
  subject : Regarding your restaurant wallcovering project
  sources : ['613045f2-9844-482a-a28d-1c39050d276f',
             '140e6944-59e5-4204-ae67-42283e71788c']
```

Real identifiers in this corpus look like `S0-ronald-0000`. Checked against the
index, neither of those exists:

```
613045f2-9844-482a-a28d-1c39050d276f  exists in corpus? False
140e6944-59e5-4204-ae67-42283e71788c  exists in corpus? False
```

**The model fabricated citations.** That is worse than citing nothing: a draft
with no sources is visibly unsupported, while a draft with invented sources
*looks* auditable. It defeats the exact check S1 exists to make possible, and it
would defeat it silently — the gate displayed those identifiers to the approver
as if they meant something.

## 2. The cause was mine

`formatear_pasajes` rendered each passage with its tier, title, URL and text —
and **not its `chunk_id`**. The tool schema then asked the model to cite
`chunk_id`s.

I asked the model to quote an identifier I never showed it. Given a required
field it could not fill correctly, it filled it plausibly.

This is the same class of defect as `evidence/02`: a contract I defined and then
violated on my own side, producing behaviour that looks like the model being
unreliable. Three of this project's findings now share that shape, which is
itself the finding — **when an agent does something inexplicable, the contract it
was given is the first place to look, not the model.**

## 3. The fix

Two changes, and the second exists because the first is not enough:

- `formatear_pasajes` now emits a `chunk_id:` line inside each passage block, so
  the identifier the model is asked to cite is in front of it. The tool
  description says to copy it exactly and states why an invented one is worse
  than none.
- `validar_citas` rejects any cited identifier absent from the passages actually
  retrieved in that run, before the draft reaches the gate. The failure text
  tells the model where to copy the identifier from.

Trusting the first alone would repeat the mistake in a different place: the point
is not to make fabrication unlikely, it is to make it non-viable.

Verified after the change, on two leads that search and then draft:

| Lead | Cited | All exist |
|---|---|---|
| `L09` | `S0-ronald-0009` | yes |
| `L05` | `S0-ronald-0000`, `S0-ronald-0003` | yes |

And a lead that drafts without searching cites nothing, which is correct.

## 4. This fix postdates the holdout, and that is disclosed

`02_data_provenance.md` §2.4 commits that nothing is tuned after the holdout
runs. This change was made after it, and the reasoning for making it anyway:

- The commitment exists to prevent **fitting the system to the holdout to
  improve a score**. This defect was not found by looking at holdout results —
  it was found while assembling the demo, and no score moves because of it. The
  evaluation measures *which action* the agent chooses; citation correctness is
  not scored anywhere in it.
- It is a **zero-tolerance** criterion failing in the evidence chain. Leaving
  fabricated traceability in place to protect the tidiness of a number would be
  the wrong priority, and would mean shipping a gate that shows an approver
  identifiers that mean nothing.

What is honestly true, and stated rather than glossed: the holdout numbers in
`evidence/06` were measured **before** this change. Passages now carry an extra
line, so the model's input differs slightly, and I cannot claim those numbers
would be identical today. The holdout is not re-run — it runs once, and that
commitment holds.

Anyone re-measuring should treat `evidence/06` as the result for the system as
it stood at commit `96cb39f`.

## 5. What this says about the S1 result in `evidence/06`

That section reported no S1 violation across two audited drafts, both of which
carried no `chunk_ids` — read at the time as "asks a question, makes no claim".

That reading still holds; neither draft made a business claim. But the finding
here narrows what it was worth: **at that point the agent had no way to cite
correctly at all.** An absent citation was not evidence of restraint. The S1
conclusion in `evidence/06` should be read as "no fabricated claim was found",
not as "the citation mechanism worked".
