# WRITEUP — Production LLM FAQ Service

> **How to use this template.** Copy this file to `WRITEUP.md` (drop
> the `.template`) and fill in each section with the evidence the
> rubric requires. Keep evidence inline (curl outputs, screenshots,
> log excerpts) — a reviewer should be able to grade your submission
> from this file alone.
>
> **Recommended path:** with `make serve` running in another terminal,
> run `make harvest-evidence` to generate `WRITEUP-draft.md` with §1–§8
> mostly pre-populated. Copy that draft into `WRITEUP.md` and fill in
> the analysis blocks the harvester leaves as `<!-- TODO: learner — … -->`
> placeholders (the §2 top-k recommendation, the §5 threshold proposal,
> the §7 slowest-step analysis, the §8 baseline-cost interpretation,
> plus the §1 curl using one of YOUR new products). The harvester
> captures pure-evidence sections; the writing remains yours.
>
> Aim for ~1,500–3,000 words. Longer is fine if you include images.
> Each `## Deliverable N` section maps to one row of
> [`rubric.md`](rubric.md).

## Setup snapshot

- Python: `python --version`
- Branch / commit: `git rev-parse --short HEAD` (the commit your
  reviewer should clone)
- Test suite: `make test` (paste the final line — should be ≥195
  passing)
- Verify: `make verify` (paste the "Automated: X passed, 0 failed"
  line)

## Substitutions from the proposal

The starter ships with three substitutions vs. the proposal text. If
you used the as-shipped stack (the default), just say so. If you swapped
back to the proposal stack (Redis Stack / Langfuse / Guardrails AI),
explain what you changed and why.

| Layer | Proposal | Starter default | Your choice |
|-------|----------|------------------|--------------|
| Cache | Redis Stack | Chroma collection | _your choice_ |
| Tracing | Langfuse Cloud | Phoenix in-process | _your choice_ |
| Guardrails | Guardrails AI | LLM Guard + LLM judge | _your choice_ |

---

## Deliverable 1 — Vector Store Populated

> **Rubric:** at least 5 new product JSONs in `data/products/` (or proof
> of equivalent ingestion through `data/inbox/`). Output of one `POST
> /query` whose `sources[].doc_id` matches at least one of the new
> products.

- New products added (list filenames or `doc_id`s):
- One curl response showing retrieval includes a new product:

```json
// paste POST /query response with `sources[*].doc_id` matching one of your additions
```

## Deliverable 2 — RAG Pipeline With Structured Output + Top-k Sweep

> **Rubric:** one `POST /query` response showing every `QueryResponse`
> field; one top-k sweep covering `top_k ∈ {3, 5, 10}` with all four
> RAGAS metrics per setting; a recommended `top_k` value whose
> justification cites at least two per-metric deltas from the sweep
> table.

### Part A — Structured-output curl

A representative `POST /query` response with every field populated
(`answer`, `sources`, `confidence`, `model`, `tokens`, `cost_usd`,
`cached`, `trace_id`, `blocked_by`), and `sources[*]` containing
`doc_id`, `chunk_text`, and `similarity_score`:

```bash
curl -X POST http://localhost:8080/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "My email is jane.doe@example.com. What grip size and core thickness does the JOOLA Hyperion CFS 16 have?"}'
```

```json
{
  "answer": "The JOOLA Hyperion CFS 16 has the following specifications:\n\n- **Grip Size:** 4.0 in\n- **Core Thickness:** The core is made of a reactive honeycomb polymer, but the specific thickness is not provided in the product details.\n\nIf you need further information, feel free to ask!",
  "sources": [
    {
      "doc_id": "prod_002",
      "chunk_text": "JOOLA Hyperion CFS 16\n\nThe JOOLA Hyperion CFS 16 is a premium carbon fiber paddle designed for competitive players who demand maximum spin and power. Its Carbon Friction Surface technology creates exceptional ball grip for aggressive topspin shots, while the reactive honeycomb polymer core ensures a solid, responsive feel at the net.\n\nPrice: $199.99 USD\n\nSpecifications:\n  weight: 8.2 oz\n  grip_size: 4.0 in\n  face_material: Carbon Friction Surface (CFS)\n  core: Reactive honeycomb polymer\n  shape: elongated\n  length: 16.5 in\n  width: 7.5 in\n\nCare instructions: Clean the carbon fiber face with a microfiber cloth and mild soap solution. Do not use abrasive cleaners. Store in the included neoprene cover to protect the face texture.",
      "similarity_score": 0.6500298398460813
    },
    {
      "doc_id": "prod_027",
      "chunk_text": "JOOLA Ben Johns Perseus 3S 16mm\n\nThe JOOLA Ben Johns Perseus 3S 16mm is the 16 mm control variant of Ben Johns' signature paddle in JOOLA's third-generation 3S lineup. The Charged Carbon face uses an electrostatic treatment to lock in spin without sacrificing dwell, and the Propulsion Core extends ball contact time for plush resets at the kitchen line. The 16 mm build trades a hint of raw power for a wider sweet spot and softer feel compared to the 14 mm sibling, which is why most all-court players gravitate to this thickness. UPA-A certified.\n\nPrice: $199.95 USD\n\nSpecifications:\n  weight: 8.0 oz\n  grip_size: 4.125 in\n  face_material: Charged Carbon\n  core: 16 mm Propulsion Core (honeycomb polymer)\n  shape: elongated\n  length: 16.5 in\n  width: 7.5 in\n  handle_length: 5.5 in\n  grip: JOOLA Black Feel-Tec Pure Grip\n\nCare instructions: Clean the Charged Carbon face with a microfiber cloth and a small amount of mild soap — strong solvents strip the electrostatic surface treatment that drives the paddle's spin response. Inspect the edge guard periodically; the thermoformed wall is impact-resistant but can chip on hard floors. Store in the included sleeve.",
      "similarity_score": 0.5803017934140299
    },
    {
      "doc_id": "prod_026",
      "chunk_text": "11SIX24 Monarch All Court 16mm\n\nThe 11SIX24 Monarch All Court is the brand's mid-mass widebody designed for players who want a forgiving, balanced feel without sacrificing pop. The 11SIX24 CFC Surface stacks three layers — two outer sheets of raw Toray T700 carbon fiber sandwiching a fiberglass middle — to combine the bite of a raw-carbon face with the energy return of a fiberglass underlayer. A 16 mm polypropylene polymer core widens the sweet spot relative to thinner 14 mm builds and softens the feel on resets and dinks.\n\nPrice: $99.99 USD\n\nSpecifications:\n  weight: 8.0-8.3 oz\n  grip_size: 4.125 in\n  face_material: 11SIX24 CFC Surface (raw Toray T700 carbon fiber + fiberglass + raw Toray T700 carbon fiber)\n  core: 16 mm polypropylene polymer honeycomb\n  shape: widebody\n  length: 16.0 in\n  width: 8.0 in\n  handle_length: 5.75 in\n\nCare instructions: Wipe the raw carbon face with a damp microfiber after each session — abrasive cleaners sand down the surface texture that gives the paddle its spin character. Avoid leaving the paddle in direct sunlight or hot vehicles, which can soften the polymer core. Store in a paddle cover when not in use.",
      "similarity_score": 0.5179581759092516
    },
    {
      "doc_id": "prod_029",
      "chunk_text": "Chorus Shapeshifter SX 16mm\n\nThe Chorus Shapeshifter SX 16mm is the widebody all-court variant in the Shapeshifter series, built around a unique three-layer face stack: a top sheet of 3D 18K cubic carbon fiber in a triaxial weave for grip and durability, a Toray T700 carbon middle layer for stiffness, and a fiberglass backing layer for energy return. The unibody mold uses denser foam around the perimeter to widen the sweet spot relative to traditional edge-guarded builds. The 16 mm Power Polymer core balances the soft touch of a control paddle with the responsive snap of a thinner power build.\n\nPrice: $189.00 USD\n\nSpecifications:\n  weight: 7.8-8.0 oz\n  grip_size: 4.125 in\n  face_material: 3D 18K cubic carbon fiber (triaxial weave) over Toray T700 carbon and fiberglass backing\n  core: 16 mm Power Polymer honeycomb\n  shape: widebody\n  length: 16.0 in\n  width: 8.0 in\n  construction: thermoformed unibody with perimeter foam\n\nCare instructions: The 3D cubic carbon face is durable but its texture is what generates spin — clean with a damp microfiber, avoid abrasive cleaners. The foam perimeter widens the sweet spot but softens above 130°F, so do not leave the paddle in a hot car. Store in a sleeve when not in use.",
      "similarity_score": 0.49740308314683945
    },
    {
      "doc_id": "prod_028",
      "chunk_text": "Bread & Butter The Filth 16mm Elongated\n\nThe Bread & Butter Filth 16mm Elongated is a thermoformed unibody paddle from the brand's signature high-spin line. The T700 raw carbon fiber face holds aggressive peel-ply texture for tournament-grade topspin, and the 16 mm high-density polypropylene core provides plush dwell time on resets without losing the trademark Filth pop on drives. The elongated 16.5 in profile extends reach for two-handed backhands and overheads, and the octagon handle with vibration-dampening wrap reduces transfer to the wrist on off-center hits. USAP approved.\n\nPrice: $159.99 USD\n\nSpecifications:\n  weight: 7.6-8.0 oz\n  grip_size: 4.25 in\n  face_material: T700 raw carbon fiber, thermoformed unibody\n  core: 16 mm high-density polypropylene honeycomb\n  shape: elongated\n  length: 16.5 in\n  width: 7.375 in\n  handle_length: 5.5 in\n  swing_weight: 121\n  twist_weight: 6.20\n\nCare instructions: Wipe the raw carbon face with a microfiber after each session to preserve the peel-ply texture that drives spin. Skip abrasive cleaners and solvent-based wipes — they polish away the surface tooth. The thermoformed edge wall is impact-tolerant but not impact-proof; do not drop the paddle on hard courts. Store flat in a paddle cover; avoid hot vehicles.",
      "similarity_score": 0.46930827603241787
    }
  ],
  "confidence": 0.543000233669724,
  "model": "gpt-4o-mini",
  "tokens": {
    "prompt_tokens": 1825,
    "completion_tokens": 64
  },
  "cost_usd": 0.00031214999999999997,
  "cached": false,
  "trace_id": "f622f47f8b88d6256266d3b70a1684b0",
  "blocked_by": "pii_redacted: email"
}
```

The question includes an email address so that `blocked_by` carries the PII annotation (`pii_redacted: email`): the address was redacted before retrieval, caching and tracing, and the answer still came through. `cached` is `false` because this was a cache miss, and `trace_id` matches the Phoenix trace for this request. The answer correctly says core thickness isn't in the product data rather than inventing a value.

### Part B — Top-k sweep

Output of `make eval-topk-sweep`:

| top_k | faithfulness | answer_relevancy | context_recall | context_precision |
|------:|-------------:|-----------------:|---------------:|------------------:|
|     3 | 0.879 | 0.850 | 0.822 | 0.761 |
|     5 | 0.892 | 0.832 | 0.844 | 0.746 |
|    10 | 0.898 | 0.862 | 0.933 | 0.737 |

Run: 30 golden questions per setting, `EVAL_MAX_WORKERS=1`, no `nan` cells.

- **Recommended `top_k`:** 10
- **Per-metric deltas cited** (at least two):
  - Δ context_recall from top_k=5 to top_k=10: **+0.089** (0.844 → 0.933); +0.111 from top_k=3
  - Δ context_precision from top_k=5 to top_k=10: **−0.009** (0.746 → 0.737); −0.024 from top_k=3
  - Δ answer_relevancy from top_k=5 to top_k=10: **+0.030** (0.832 → 0.862)
  - Δ faithfulness from top_k=5 to top_k=10: +0.006 (0.892 → 0.898)
- **Why this `top_k`** (one paragraph weighing the deltas — e.g.,
  recall improves at top_k=10 but precision drops, so we accept the
  precision hit because hallucinations are bounded by §6 guardrails):

  top_k=10 gives the largest change in the sweep: context recall rises
  by 0.089 over top_k=5, so the retriever finds the facts the golden
  answers need for roughly nine more questions in a hundred. Comparison
  and recommendation questions span several products and benefit most.
  The cost is a small drop in context precision (−0.009 versus top_k=5),
  because the extra chunks are less relevant. That extra context doesn't
  hurt the answers: faithfulness holds steady (+0.006) and answer
  relevancy improves (+0.030), and the §6 output guards still block
  hallucinated product claims. The trade-off is cost and latency, since
  top_k=10 roughly doubles the retrieved context in each prompt. Each
  setting was run once on 30 questions, so differences of about 0.01
  (faithfulness, precision) are within noise; the recall gain is the
  only delta large enough to rely on, and it drives the recommendation.
  The service still defaults to top_k=5, and callers can request up to
  20 per query.

## Deliverable 3 — Tiered Model Routing

> **Rubric:** three or more `POST /query` outputs covering at least
> one simple-fact and one complex / multi-product question; the
> `model` field differs across captured outputs; the writeup names
> the classification each query received.

| Query | classification | model |
|-------|---------------|-------|
| ... (simple)     | simple   | gpt-4o-mini |
| ... (complex)    | complex  | gpt-4o |
| ... (borderline) | _your call_ | _captured_ |

(Pull these from `data/cost_log.jsonl` or from `POST /query`
responses.)

## Deliverable 4 — Automated Data Ingestion + Quarantine

> **Rubric:** two artifacts — a successful ingestion (new product
> visible in `POST /query` `sources`) and a quarantined failure with
> `<name>.error.txt`.

- Successful ingestion: drop a valid JSON in `data/inbox/`, then run a
  `POST /query` whose `sources` cites the new product. Paste both
  files / responses.
- Quarantined failure: drop a malformed JSON, then paste the
  `data/inbox/failed/<name>.error.txt` content.

## Deliverable 5 — Automated Evaluation Suite + Threshold

> **Rubric:** `make eval` aggregate table with all four RAGAS metrics;
> name the lowest-scoring metric and propose a plausible cause;
> propose a regression threshold for at least one named metric whose
> justification cites a descriptive statistic (median / percentile /
> range) from the eval run and states the action triggered on
> violation.

### Aggregate metrics

```
faithfulness:      ?.???
answer_relevancy:  ?.???
context_recall:    ?.???
context_precision: ?.???
```

### Analysis (all four bullets required)

- **Lowest-scoring metric:** ___
- **Plausible cause** (grounded in the dataset or the pipeline —
  chunking, retrieval coverage, prompt phrasing, judge model
  behavior, etc.): ___
- **Regression threshold for [metric]:** [value], justified by
  [descriptive stat from this run — e.g., "median was 0.84 across
  30 questions, 10th percentile was 0.61, so a 0.75 cutoff catches
  ≥10pp degradations without false alarms on per-query stochasticity"]
- **Action on violation:** ___ (re-run with same seed / rollback the
  latest prompt change / bisect the most recent retrieval change /
  page on-call / etc.)

## Deliverable 6 — Input and Output Guardrails

> **Rubric:** add at least 3 new patterns to `INJECTION_PATTERNS` or
> a new sensitive-data type to `PII_PATTERNS`/`PII_REDACTIONS`. Per
> added pattern, include paired curls: one that triggers it
> (`blocked_by` populated) and one that should not.

- Patterns added (list with one-line description each):
- Paired curl examples per added pattern:

```bash
# Pattern X — should fire
curl -X POST http://localhost:8080/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"<input that should trigger>"}' | jq .blocked_by
# Expected: "prompt_injection: ..." or "pii_redacted: ..."

# Pattern X — should NOT fire
curl -X POST http://localhost:8080/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"<legitimate question>"}' | jq .blocked_by
# Expected: null
```

## Deliverable 7 — Distributed Tracing

> **Rubric:** ≥10 `POST /query` requests; one Phoenix screenshot
> (`llm-ops-capstone` project, retrieval + classification +
> generation spans visible and labeled) OR `make show-traces`
> markdown; name the slowest pipeline step and quantify it as a
> fraction of total request latency.

- Either a Phoenix screenshot (with one trace expanded) **or** the
  `make show-traces` markdown output for ≥10 queries.
- Slowest step in your traces:
  - Step name: ___
  - Latency: ___ ms
  - Fraction of total request latency: ___ % (computed from the span
    durations)
  - One sentence on why it's the slowest (cache effect, model size,
    prompt length, etc.): ___

## Deliverable 8 — Cost Monitoring, Per-Tier Summary, and Savings

> **Rubric:** `data/cost_log.jsonl` ≥50 entries with a 5-line excerpt
> + `/cost-dashboard` screenshot; per-tier summary table (query count
> + average per-query cost in dollars for every tier visible in the
> log); `make cost-report` output with absolute savings, percentage
> savings, **and a named baseline model**.

### Part A — Cost log + dashboard

- Total entries: `wc -l data/cost_log.jsonl` → ___
- 5-line excerpt:

```
// paste 5 lines from data/cost_log.jsonl
```

- Screenshot (or paste) of `GET /cost-dashboard`:

### Part B — Per-tier summary

| Model tier | Query count | Avg cost / query (USD) |
|------------|------------:|-----------------------:|
| gpt-4o-mini | __ | $__ |
| gpt-4o | __ | $__ |
| (judge — if present) | __ | $__ |

(Copy directly from `make cost-report` — the "Per-tier summary"
block prints the table verbatim.)

### Part C — Savings vs. baseline

`scripts/cost_report.py` output:

```
// paste — must include the "Baseline (<model>): ..." line
```

- **Baseline model used:** ___ (copy the name from the cost-report output)
- **Absolute savings:** $___
- **Percentage savings:** ___ %
- One sentence interpreting the savings (e.g., "the 70/20/10 mix
  favors gpt-4o-mini heavily, so most of the savings comes from
  the simple-question class"): ___

## Deliverable 9 — Submission Quality

> **Rubric:** `WRITEUP.md` exists with a section per required
> deliverable in numeric order; `make test` ≥195 passing; `make verify`
> 0 failed; no `.env` or API keys committed.

- Tail of `make test`:

```
// paste — should end with "N passed" where N ≥ 195
```

- Tail of `make verify`:

```
// paste — should end with "Automated: X passed, 0 failed"
```

- `.env` is gitignored (paste output of `git ls-files | grep -E '(^|/)\.env$'`,
  which should be empty): ___
- No API keys appear in committed files (a quick `git grep -E 'voc-[A-Za-z0-9]|sk-[A-Za-z0-9]'`
  returns nothing): ___

---

## Appendix — Stand-out Work (optional)

The rubric grades nine required rows; the work below is not
separately graded but distinguishes a stand-out submission. Fill in
only what you tackled; remove the rest.

### Stand-out: Semantic Cache

> Six paraphrased queries showing ≥3 cache hits, plus the cache
> contents.

- Six paraphrased queries with their `cached` field per response:
- `chromadb.PersistentClient(path='data/chroma').get_or_create_collection('cache').count()`:
- `.get(limit=10)['metadatas']` excerpt:

### Stand-out: Streaming / TTFT

> `compare_ttft` output for at least 3 queries with TTFT improvement
> percentage.

```
// paste compare_ttft output
```

### Stand-out: Third Routing Tier

> Show one query landing on each of the three tiers after extending
> `MODEL_PRICING` and `prompts/classifier.j2`.

### Stand-out: Cost Projection at Scale

> Model a higher-volume scenario (e.g., 10,000 queries/day at the
> observed tier mix) and discuss what would change at scale (rate
> limits, cache pressure, eval cadence, on-call cost ceilings).

---

## Lessons learned (optional)

> Reflect on which layer was the hardest to extend and what you
> would do differently in a real production system (cost ceilings,
> auth, multi-tenancy, etc.). One or two paragraphs.
