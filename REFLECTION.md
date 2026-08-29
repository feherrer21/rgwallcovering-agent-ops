# Reflection

## What was built

An agent working Ronald Giraldo's follow-up queue at RG Wallcovering & Painting,
Providence. Given one enquiry it decides what happens next — ask the question
that unblocks the job, offer the assessment visit, propose a time from his diary,
or hand the lead over — and stops before anything a customer would see. Four
tools, two read-only and two behind a human gate. LangGraph over Portkey, on
`gemini-2.5-flash`.

The user is Ronald, not the visitor. The certified L1 project serves visitors and
stops when the enquiry reaches his inbox — which is where the cost sits: it then
waits on a person who is on a ladder.

## Why an agent, and the test I set to prove it wasn't one

Before building I committed to a falsifier: a deterministic four-branch script
runs the same evaluation, and **if the agent agrees with it on 90% or more of
leads, the agent did not earn its place and this document says so.**

It agreed on **64%** of the design set and **33%** of the holdout: convergence
where the script's branches were written against the cases, divergence on unseen
data.

But agreement is not accuracy. **The script scored 13/14 against the agent's
12/14.** It is more accurate, and it can be steered by anything a stranger types
into a form: on `L18` it read "Tuesday" inside an injected instruction and
proposed a meeting. The agent treated it as content and escalated.

## What failed

**The agent over-escalates, and it generalises.** Both design-set misses share
one mechanism: a gap in what it can confirm becomes a handoff even when enough
is confirmable to act. On `L16` an uncovered question about hardwood floors
stalled covered work. The holdout reproduced it on `L15` (drywall) and then
produced the finding that matters most: **`L07`, the clean control, was escalated
because "January" might mean this year or next** — a lead with measurements, a
style, both channels, nothing adversarial. The control existed to catch an agent
that escalates everything. It caught mine.

**My fix made it worse.** A prompt instruction separating "unverified" from "not
yours to decide" took correct from 12/14 to 11/14 and unstable leads from 0 to 2.
Three leads moved, none to the right answer, and `L14` — previously right — began
acting on a scope it hadn't resolved. I reverted rather than iterate: fourteen
leads is small enough that more attempts would produce a prompt fitted to
fourteen cases, and the holdout would then measure the fit, not the system.

**Three failures were mine, and two nearly shipped as findings about the model.**

I marked `L09` wrong because I had recorded the service area as "tier B only" — a
sentence carried from the L1 provenance note, true when written and false at the
corpus commit I pinned. The agent was right. Citing a claim *about* data is not
checking the data.

Worse: `decidir` appended an assistant message containing a `tool_call` with no
tool result answering it. A malformed conversation doesn't raise and doesn't fail
the same way twice — it degrades behaviour indistinguishably from an unreliable
model. I measured three runs, saw two different actions, and wrote it up as model
non-determinism, citing the predecessor's genuine coin-flip finding as support.
**It was my bug.** A test asserting every `tool_call` has a matching response
found a second instance I'd missed; with both fixed, four runs agreed.

And my evaluation could not score its own zero-tolerance criterion: the runner
never saved draft bodies, so S1 had only a boolean to work from.

**My failure injection was defeated.** `L20` carries a reserved-TLD recipient so
approving would produce a real SMTP rejection. The agent recognised the
unresolvable domain by inspection and escalated without trying — better than the
test wanted, useless as a demonstration. I replaced it by breaking the transport,
at a point that doesn't exist until the action executes.

## How I fixed what I fixed

Adding a lead's town to a corpus query drops the tier-A pricing passage below
the relevance floor — silently, returning a wrong passage rather than none. That
fix went into the **tool contract**, not the prompt: it is knowledge about this
corpus.

The recovery message now names *which stage* failed. It didn't, and the agent
told Ronald an email couldn't be prepared for approval — when it had been
prepared and he had approved it. It was wrong about where in its own pipeline it
stood, not about the world.

## What I would do differently

The over-escalation is not a prompt problem, and treating it as one cost me a
regression. **The action space cannot express partial progress.** An enquiry that
is 80% actionable and 20% unanswerable has no move meaning "do the 80%, flag the
20%", so the 20% takes the whole lead. That is architecture.

I would also stop assuming the expensive model is better. `claude-opus-5` cost
3.7× the tokens, took 2.3× as long, and scored one lead *lower*, because it
escalates more — and escalating more is the failure mode.

## Business impact

Stated honestly: measured accuracy does not yet beat four `if` statements. What
the agent buys is resistance to injected instructions and a contradiction check
that is semantic rather than lexical — `L03` was held out to catch a keyword
shortcut, and the agent caught a claim in which the word "visit" never appears.

All four real seed enquiries were told the
assessment visit was free because they were nearby. The owner corrected that on
2026-08-14: it is charged, identically, for everyone. Four real people hold a
promise this business will not honour. An agent that checks a record against the
corpus and refuses to follow up on top of a false commitment is worth more than
one that answers faster.

Where I would not trust it: any lead partly outside the corpus, and any clean
lead containing a minor ambiguity. It hands both to Ronald — who was going to
look anyway.
