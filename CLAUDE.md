# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Production-style RAG FAQ service for ThirdShotHub (pickleball e-commerce), built for a Udacity LLM Ops capstone. `INSTRUCTIONS.md` lists the 9 graded deliverables; `WRITEUP.template.md` is the submission template.

## Commands

Run from the repo root:

```bash
make setup      # uv sync
make test       # no API keys or network needed
make load-data  # embed data/products into Chroma (needs OPENAI_API_KEY in .env)
make serve      # API on :8080, Phoenix UI on :6006

# Single test
uv run pytest tests/gateway/test_routes.py::test_health_returns_ok -q
uv run pytest tests/gateway/test_routes.py -k health -q
```

`make help` lists the other targets. Scripts run outside `make` need `PYTHONPATH=.`. No linter or formatter is configured.

**Costs money:** `make eval` (~$0.03) and `make eval-topk-sweep` (~$0.10) make real OpenAI calls, so don't run them in a loop. Both default to one worker because the Vocareum proxy throttles parallel calls and produces `nan` metrics. Vocareum keys have a lifetime budget.

## Request flow

`POST /query` in `src/gateway/routes.py` composes every layer inline, in this order:

1. Prompt-injection check, which short-circuits to a safe response
2. PII redaction; only the redacted text reaches the cache, LLM and traces
3. Semantic cache lookup
4. `route_query` in `src/gateway/router.py`: classify as simple or complex, select the model, run `traced_pipeline` (retrieve, then generate), log cost
5. Hallucination and off-topic output guards; a flagged response is never cached
6. Cache store

`POST /query/stream` (`src/optimization/routes.py`) runs the input guards only, with no output guards over streamed tokens.

## Things that span multiple files

- **Forward-dependency rule:** packages in `src/` may only import from lower-ranked packages. `RANK` and `ALLOWED_EXCEPTIONS` in `tests/integration/test_dependency_graph.py` enforce this, and a new exception needs a documented entry there.
- **Which guards are live:** `/query` uses `src/guardrails/llm_guard/input_guards.py` (ML) and `src/guardrails/llm_judge/output_guards.py` (LLM judge). The regex guards in `src/guardrails/input_guards.py` and `output_guards.py` are not on this path. To swap implementations, change the imports in `routes.py`.
- **Slow imports:** importing `src.gateway` builds the LLM Guard scanners at module import, which loads transformer models and can take minutes. `tests/conftest.py` stubs them, along with Phoenix and the `chromadb` and `openai` constructors, before any test imports run. Test through pytest rather than ad hoc `python -c` imports.
- **Standalone wrappers:** `guarded_route_query` and `cached_route_query` exist for tests and isolated exploration only. Changes to the production flow belong in `routes.py`.
- **Inbox watcher runs in-process:** the FastAPI lifespan starts it because `chromadb.PersistentClient` has no cross-process cache invalidation. Running the watcher separately alongside the server leaves the server's index stale until restart.
- **Working directory matters:** `data/chroma`, `data/phoenix`, `data/cost_log.jsonl` and `data/inbox` resolve relative to the current directory, so run from the repo root. `prompts/` resolves relative to the source file.
- **Tracing backend:** `src/tracing/__init__.py` picks it at import time from `TRACING_BACKEND` (`phoenix` or `none`). Spans go to the `llm-ops-capstone` Phoenix project, not `default`.
- **Classifier fallback:** bad JSON from the classifier routes to the complex tier, so check this first if routing skews toward `gpt-4o`.
- **`blocked_by` is not always a block:** `pii_redacted: ...` is an annotation on a successful answer. Presidio often flags brand names like "Selkirk" as `person`.
- **Prompt context markers:** `prompts/rag_system.j2` wraps retrieved context in `<<<BEGIN_CONTEXT>>>` markers as the indirect prompt-injection defense. After changing them, run `tests/gateway/test_routes.py`.
- **Dependency pins:** `arize-phoenix<14`, `arize-phoenix-evals<3` and `llm-guard` conflict through `cryptography`, so bump them together. `ragas` is pinned exactly because 0.x patches break. The reasons are in `pyproject.toml` and the README's Dependency Notes.

## Where the docs are out of date

Trust the code over the README on these:

- It describes `/query` guards as regex-based; they are ML and LLM-judge based.
- It gives the cache threshold default as 0.95; `lookup` defaults to 0.85.
- It cites 195 tests; there are 231.
- `rubric.md` and `docs/verifications/`, referenced in the README and `src/config.py`, don't exist in this repo.

## Commits

Commit frequently with short, meaningful messages. Saurabh must be the only contributor, so don't add `Co-Authored-By` trailers or other attribution.
