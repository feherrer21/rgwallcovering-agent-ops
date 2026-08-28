# Finding: the agent can fail S3 by querying badly, not by reasoning badly

**Date:** 2026-08-28
**Found during:** T0.6, the first round trip through the gateway — before the
graph existed.
**Criterion at risk:** S3 (a record contradicting the corpus must be surfaced,
not repeated).

---

## What happened

The first end-to-end call was given a seed lead's claim and asked to verify it:

> *"A lead record says: 'I told her the assessment visit isn't charged since
> Pawtucket is nearby.' Verify that before we follow up."*

`@dsvertex/gemini-2.5-flash` correctly decided to call `buscar_corpus`. It chose
the query:

```
"is the assessment visit charged in Pawtucket"
```

That returned **one passage, tier C**. The tier-A passage confirmed by the owner
— the one that says the visit is charged, identically, regardless of distance —
was not in the result.

## The mechanism

Measured directly against the index, holding the relevance floor at 0.62:

| Query | Passages | Tier A returned? | Best tier-A score |
|---|---|---|---|
| `is the assessment visit free` | 3 | **yes** | 0.677 |
| `is the assessment visit charged` | 4 | **yes** | — |
| `is the assessment visit charged in Pawtucket` | 1 | **no** | below floor |
| `does the assessment fee depend on distance` | 4 | **yes** | 0.742 |
| `how much does the assessment visit cost` | 4 | **yes** | 0.727 |

Four of five phrasings retrieve the passage. The one that does not is the one
the model chose.

The corpus contains no document about Pawtucket, or about any individual
customer or address — it describes the business. Adding a place name moves the
query embedding away from the region where the pricing document sits and drops
its cosine below the floor.

**The failure is silent.** The tool does not error and does not return empty. It
returns a passage — the wrong one, at tier C, which by the tier rules may only
be used to explain what *determines* an answer and may never be phrased as
something the company does. An agent working from that result has no way to
detect the contradiction, and its most likely next move is to proceed with the
follow-up, repeating a promise the business will not honour.

So S3 can fail for a reason that has nothing to do with the model's judgement.

## Why the frontier model did better, mechanistically

On the same prompt, `@aws-bedrock-use2/us.anthropic.claude-opus-5` issued **two**
tool calls rather than one:

```
buscar_corpus({"consulta": "is the assessment visit charged"})
buscar_corpus({"consulta": "do you cover Pawtucket Rhode Island"})
```

This is not "the bigger model is smarter". It decomposed a compound claim — a
rule (*not charged*) and a reason (*because nearby*) — into two queries, which
kept the location token out of the policy query and left that query in the range
where the tier-A document scores 0.71–0.76.

The measured difference is in **query construction**, not in reasoning about the
result. That distinction matters, because it is fixable without a bigger model.

## What was changed as a result

The tool description now instructs the model to query the policy rather than the
lead, to omit names, towns and specifics, and to split a compound claim into one
query per part. The fix is in the tool contract rather than in the system
prompt, because it is knowledge about *this corpus*, and it belongs where the
model reads about the corpus.

Whether the instruction is sufficient is an open question, not a claim. It is
re-measured against the design set in Phase 6.

## Cost of the two models on this call

| Model | Latency | Total tokens | Reasoning tokens |
|---|---|---|---|
| `gemini-2.5-flash` | 1.6 s | 351 | 104 |
| `gemini-2.5-flash-lite` | 1.3 s | 360 | 113 |
| `claude-opus-5` | 4.1 s | 968 | 0 |

Noted separately because it is easy to forget: Gemini 2.5 spends output tokens
on reasoning before emitting content. A first attempt with `max_tokens=20`
returned `finish_reason: "length"` and an assistant message with **no content
field at all** — 16 tokens spent, all of them reasoning. That does not look like
an error and is one, which is why the model client sets an explicit token budget
rather than relying on a default.
