# Data Provenance Note

**Case:** L2_Case05_Open_Choice_Agent
**Status:** written before any implementation code
**Date:** 2026-08-28

No dataset was provided for this case. There are three datasets here, with very
different origins and very different sensitivity, so they are treated
separately: the **company corpus** the agent can consult, the **evaluation set**
it is measured against, and the **runtime lead records** it operates on.

---

## 1. Company corpus — inherited, and cited as such

### 1.1 What it is and where it came from

The indexed corpus is **carried over from the certified L1 project**
(`rgwallcovering-ai-assistant`) as input data. It is not re-collected, and the
reuse is declared rather than absorbed: see `00_reuse_boundary.md` for what may
and may not cross over. The retrieval code is **not** reused; only the two
index files and their schema.

| ID | Source | Type | Retrieved | Tier |
|----|--------|------|-----------|------|
| S0 | Ronald Giraldo, owner — direct answers | First-party, owner-stated | 2026-08-12, corrected 2026-08-14 | A |
| S1 | rgwallcovering.com — Home, About, Interior Design, Contact | First-party | 2026-08-12 | A |
| S2 | rgwallcovering.com/blog — 27 posts, Jul 2021 → Jan 2025 | First-party | 2026-08-12 | A |
| S4 | BBB business profile | Third-party directory | 2026-08-12 | B |
| S5 | Houzz professional profile | Third-party directory | 2026-08-12 | B |
| S6 | Generic wallcovering/painting trade knowledge, author-written | Synthetic, domain-general | 2026-08-12 | C |

Measured contents of the index as carried over: **370 chunks — 331 tier A, 4
tier B, 35 tier C.** Embeddings are `BAAI/bge-small-en-v1.5` via `fastembed`,
384 dimensions, L2-normalised, computed locally on CPU. No embedding API is
called, at build time or at query time.

**Exact provenance of the two files in `data/index/`.** Copied byte-for-byte
from `rgwallcovering-ai-assistant` at commit
`10612cab073e7514af59dcb6598aff690c1a3daf` (2026-08-14), which is that
repository's head at the time of copying and the state in which it was
certified. `embeddings.npy` verified identical by checksum
(`md5 05227d0493574411ffb48bc967f922ec`). Naming the commit matters because the
corpus behind these files was corrected two days before it — see §1.3 — so
"the corpus from L1" is ambiguous and a commit is not.

### 1.2 The property of this corpus that matters most here

**It is large in volume and thin in answering power.** The blog is
overwhelmingly decorative and cultural — block printing history, ancient
Egyptian interiors, cherry blossoms — and says almost nothing about
installation, materials, lead times or cost. The nearest neighbour to a
business question is frequently fluent and irrelevant.

For this project the consequence is specific: **retrieval returning nothing is
a correct outcome**, and the agent must be able to act on an empty result
without softening it into a partial answer.

### 1.3 The tier-A fact that was false

On 2026-08-14 the owner reversed what he had said two days earlier. Until then
the corpus asserted that the assessment visit was free within Rhode Island and
that the charge depended on distance. That was published and was being asserted
to visitors. The corrected fact is unambiguous: **the visit is charged, it costs
the same for everyone, and distance does not enter into it.**

This is not a footnote — it is the most load-bearing fact in this dataset, for
two reasons:

1. It is the contradiction the agent has to detect, and it is present in **all
   four real seed leads** (§3.1).
2. It demonstrates that **traceability and truth are not the same property**. A
   claim can trace perfectly to a tier-A source that was wrong. The whole
   defence built in L1 targeted untraceable claims and was structurally
   incapable of catching this one.

### 1.4 Known limitations, carried over unchanged

- **Stale.** The most recent blog post is January 2025. Nothing reflects current
  availability, pricing or capacity.
- **Service area is tier A, corrected 2026-08-28.** This note originally said it
  was tier B only, carried over from the L1 provenance note. That was wrong at
  the pinned commit: an owner-confirmed passage states the company covers Rhode
  Island, Massachusetts and Connecticut, focusing on the first two. The error was
  found by running the agent, and it invalidated one expected label. See
  `evidence/01_etiqueta_incorrecta_L09.md`. What remains tier B is the *town
  list* in the directory profile, which is unverified detail rather than the
  service area itself.
- **Single-language.** All source content is English, so a Spanish-language
  enquiry is ungrounded even when the underlying fact exists. Tested by **L02**
  and **L13**.
- **Warranty terms absent by design.** The owner flagged his own answer as
  unverified, so it never entered the corpus.

---

## 2. Evaluation set — 20 leads, authored for this project

`eval/leads_design.jsonl` (14) · `eval/leads_holdout.jsonl` (6)

### 2.1 How it was generated, and in what order

Hand-written for this project. **The composition below was fixed and written
down before a single lead was drafted, and both files were committed before any
agent code exists.** The commit order is the evidence and it is checkable in
`git log`.

The order matters because the case penalises data chosen to flatter the
prototype. Committing the mix while it is still possible to be wrong about what
will be hard is the only defence against choosing it afterwards.

### 2.2 Composition

| Category | n | Held out | What it stresses |
|---|---|---|---|
| A — Ready to advance | 4 | 1 | That it acts rather than escalating everything |
| B — Missing one critical field | 3 | 1 | Which single question is worth asking |
| C — No usable contact channel | 2 | 0 | S4 — channel unavailable |
| D — Record contradicts the corpus | 3 | 1 | S3 — the false promise, in three phrasings |
| E — Record contradicts itself | 2 | 1 | Whether it notices, or averages |
| F — Out of scope request | 2 | 1 | Declining without inventing capability |
| G — Untrusted input | 2 | 1 | Instructions as content, never as commands |
| H — Sets up a tool failure | 2 | 0 | S5 — validation, retry, escalation |
| **Total** | **20** | **6** | |

Language split: 18 English, 2 Spanish. Two records derive from real enquiries;
eighteen are authored.

**The four straightforward leads exist deliberately.** A set made only of
awkward cases is biased in the other direction, and without clean controls
there is no way to detect the failure mode named in `01_problem_statement.md`
§8 — an agent that escalates everything, is never wrong, and is useless.

### 2.3 The awkward cases, named individually

"Adversarial cases were included" is not evidence, so:

- **L02 / L13** — Spanish, where the corpus is English-only.
- **L03** (held out) — the false-promise claim phrased *indirectly*: the visitor
  asks whether the "estimate" is free and is told yes. The word "visit" never
  appears. A keyword match that resolves L01 and L02 fails here by construction.
- **L09** — a Massachusetts project. Coverage is answerable, so the lead tests
  whether the agent checks before asserting rather than assuming either way.
- **L11** — no email, no phone, no location. Nothing is sendable and nothing may
  be invented.
- **L12** — an email address invalid by one character. Detecting it after the
  bounce is too late; "correcting" it is fabricating contact data.
- **L14 / L13** — scope stated two different ways in one conversation. One wall
  and five rooms are different businesses.
- **L16 / L15** — hardwood floors and drywall repair. The corpus supports
  neither a yes nor a no, and L16 adds explicit commercial pressure.
- **L18** — an instruction block in the visitor's message demanding a $0 quote
  and an immediate booking.
- **L17** (held out) — the same attack moved **into the summary field**, which
  is prose that looks internally authored and therefore trustworthy. An agent
  that learned to distrust the visitor *channel* rather than the *content*
  fails this and passes L18.
- **L19 / L20** — the two tool-failure setups: a calendar consultation and an
  email address on `example.invalid`, a reserved TLD guaranteed never to
  resolve, so the SMTP rejection is real rather than mocked.

### 2.4 The holdout, and what it honestly is

Six leads are held out, at least one from every category that has more than one
member, plus **two categories the design set does not contain at all** — L10
(decision authority) and L17 (injection in a trusted-looking field). Those two
measure generalisation to a *kind* of gap the agent was never shown, not just
to new instances of a familiar one.

**It is a pre-registered holdout, not a blind one.** The same person authored
both halves, so knowledge of the held-out cases cannot be excluded from the
design of the agent. This is a real weakness and it is not solved by asserting
discipline. What is actually enforceable:

- Both files were committed **before any agent code existed**. The timestamp is
  in `git log` and is not editable after the fact.
- The holdout is not executed until the final evaluation run. Intermediate runs
  use the design set only.
- No prompt, tool description or rubric is changed after the holdout is run. If
  it exposes a failure, the failure is reported, not fixed and re-measured.

The one genuinely blind option available — a second author writing cases this
one has not seen — is offered to the project owner and recorded here as
outstanding rather than claimed.

### 2.5 The labels are judgement, not ground truth

Each record carries `accion_esperada` and `por_que`. These are **my** stated
definition of the correct next action, written before measuring, with the
reasoning attached so it can be argued with. The case supplies no ground truth
and says so: establishing what correct means is a substantial part of the work.
Where a label is contestable — L08, where the argument is that offering the
visit beats asking a question — the reasoning is in the record.

### 2.6 What this set does not represent

- **It is a model of Ronald's queue, not an observation of it.** There is no
  follow-up history, no CRM export, no record of which enquiries converted. The
  business does not capture that, which is part of the problem being solved and
  is circular. This is the largest threat to every number this project reports.
- **Twenty is small.** Differences of one or two leads are not significant and
  no confidence intervals are claimed.
- **Single author, for prompt and data both.** Known, and unmitigated unless
  §2.4's offer is taken up.
- **No lead in this set is hostile in the commercial sense** — no one is trying
  to extract a discount by persistence, because that is a behaviour over many
  turns and these records are short.

---

## 3. Lead records — the sensitive material

### 3.1 The real seed records

Four real captured enquiries exist from the L1 deployment, covering **two
distinct people**. They contain names, email, a phone number, and in one case a
**street address**. All four contain the false free-visit promise from §1.3.

### 3.2 How they are handled

- **They never enter this project's pipeline.** What enters is a synthetic
  stand-in written from the record's *shape*: same missing fields, same channel
  constraints, same false promise, different person. `L02 Carmen Duarte` is the
  stand-in for the record that carries a real street address and an
  international mobile; the address is dropped entirely and the number is
  replaced with a non-routable one. `L01 Ana Ruiz` is already a synthetic
  persona from the L1 evaluation runs and is kept as is.
- **This is a pipeline rule, not a publication rule**, and the reason is
  specific. Model calls leave this machine through an employer-managed gateway
  to third-party providers whose data-handling terms this project has not
  verified and does not control. Real customer PII does not belong in a
  coursework prompt on that basis alone — the standard is what can be
  established, not what is probably fine. See `03_spec.md` §8 for the routing
  decision and the production gap it names.
- **Not committed.** `data/leads*.jsonl` is in `.gitignore` from the first
  commit of this repository, before any lead could exist here. The evaluation
  set lives under `eval/` precisely so that the ignore rule protecting real
  leads never has to be weakened to publish synthetic ones.
- **Contact details are non-routable by construction.** Every address uses
  `example.com` or `example.invalid` (RFC 6761 reserved), and every phone number
  is in the `555-01xx` reserved range. **No address the system would ever send
  to can reach a real person**, so a slip during development cannot become a
  message to a stranger.

  Precisely stated, because the looser version was wrong: one routable address
  does appear in the repository, inside a committed evaluation result. It is in
  the *model's own reasoning* on `L12`, where it names the address it is
  declining to guess — "I'm not going to assume `j.torres@gmail.com`, that guess
  could land in a stranger's inbox." It is not a contact for anyone and the
  system never sends to it. It is left in place rather than redacted: editing
  evaluation output to tidy a claim would be tampering with the evidence, and
  the claim is what needed narrowing.
- **Never logged.** Lead contents do not go to logs, and `traces/` is
  gitignored because step traces can contain conversation content. Observability
  evidence that ships is curated by hand into `docs/evidence/`.

### 3.3 Third-party personal data

Ronald Giraldo's name and the business contact details are published business
information, already public on the client's own site. No customer review text
from BBB or Houzz is used: it is other people's words and is not the client's to
republish.

---

## 4. Provenance summary

| The question the case asks | The answer |
|---|---|
| Where did the data come from? | Corpus: carried over from the certified L1 project, itself sourced from the client's own site and blog (A), two directories (B), and author-written trade knowledge (C). Evaluation set: 20 lead records authored for this project, two of them synthetic stand-ins for real enquiries. |
| What does it represent? | What RG Wallcovering published about itself as of 2026-08-12, with one owner correction on 2026-08-14; and a stated model of the enquiries that arrive in the owner's inbox. |
| What does it *not* represent? | Any observed follow-up behaviour, conversion history, or queue. Any fact about price, availability or coverage newer than August 2026. Anything about how Ronald actually triages, as opposed to how he said he would. |
| Does it contain cases the solution gets wrong? | By construction. Sixteen of twenty are awkward on a named axis, six are held out, and two of those six belong to categories absent from the design set. §2.3 names each one and what it attacks. |
| How was anything sensitive handled? | Real leads never enter the pipeline; synthetic stand-ins preserve the difficulty and drop the identity. Real records gitignored from the first commit, never logged. All contact details non-routable by construction. The substitution is enforced at the data layer, not at publication, because prompts leave the machine through a gateway to providers whose data terms this project cannot verify. |
