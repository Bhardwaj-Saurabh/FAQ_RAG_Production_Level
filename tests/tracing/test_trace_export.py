"""Tests for src.tracing.trace_export rendering helpers."""

import json

import pandas as pd

from src.tracing.trace_export import (
    render_json,
    render_markdown,
    summarize_traces,
)


def _two_span_trace(trace_id: str = "trace_a") -> pd.DataFrame:
    """Build a synthetic Phoenix span DataFrame: one root + one child.

    Mirrors the column shape Phoenix actually emits — nested span
    attributes under ``rag.*`` flatten into a single dict-valued
    column ``attributes.rag``, not into per-key flat columns. Token
    counts live on the ``rag_generation`` child span, not the root.
    """
    return pd.DataFrame(
        [
            {
                "context.trace_id": trace_id,
                "name": "rag_query",
                "parent_id": None,
                "start_time": pd.Timestamp("2026-04-29 12:00:00"),
                "end_time": pd.Timestamp("2026-04-29 12:00:01"),
                "attributes.input.value": "How heavy is the Selkirk?",
                "attributes.rag": {
                    "model": "gpt-4o-mini",
                    "latency_ms": 850.0,
                },
                "attributes.llm.token_count.prompt": None,
                "attributes.llm.token_count.completion": None,
            },
            {
                "context.trace_id": trace_id,
                "name": "rag_generation",
                "parent_id": "root",
                "start_time": pd.Timestamp("2026-04-29 12:00:00.100"),
                "end_time": pd.Timestamp("2026-04-29 12:00:00.900"),
                "attributes.input.value": None,
                "attributes.rag": None,
                "attributes.llm.token_count.prompt": 120,
                "attributes.llm.token_count.completion": 30,
            },
        ]
    )


# --- summarize_traces -------------------------------------------------------


def test_summarize_traces_groups_by_trace_id():
    df = _two_span_trace()
    summaries = summarize_traces(df, last_n=10)

    assert len(summaries) == 1
    s = summaries[0]
    assert s["trace_id"] == "trace_a"[:8]
    assert "How heavy" in s["question"]
    assert s["model"] == "gpt-4o-mini"
    assert s["latency_ms"] == 850.0
    assert s["prompt_tokens"] == 120
    assert s["completion_tokens"] == 30


def test_summarize_traces_identifies_slowest_child():
    df = _two_span_trace()
    summaries = summarize_traces(df, last_n=10)

    s = summaries[0]
    assert s["slowest_span"] == "rag_generation"
    # 0.1s start, 0.9s end → 800ms
    assert s["slowest_ms"] == 800.0


def test_summarize_traces_handles_empty_df():
    summaries = summarize_traces(pd.DataFrame(), last_n=10)
    assert summaries == []


def test_summarize_traces_returns_at_most_last_n():
    rows = []
    for i in range(15):
        rows.extend(
            _two_span_trace(trace_id=f"trace_{i:02d}").to_dict("records")
        )
    df = pd.DataFrame(rows)

    summaries = summarize_traces(df, last_n=5)
    assert len(summaries) == 5


def test_summarize_traces_skips_traces_with_no_root():
    """A trace that only contains child spans is silently skipped."""
    df = pd.DataFrame(
        [
            {
                "context.trace_id": "orphan",
                "name": "rag_generation",  # no rag_query parent
                "parent_id": "missing_root",
                "start_time": pd.Timestamp("2026-04-29 12:00:00"),
                "end_time": pd.Timestamp("2026-04-29 12:00:01"),
                "attributes.input.value": None,
                "attributes.rag": None,
                "attributes.llm.token_count.prompt": None,
                "attributes.llm.token_count.completion": None,
            }
        ]
    )
    summaries = summarize_traces(df, last_n=10)
    assert summaries == []


# --- render_markdown --------------------------------------------------------


def test_render_markdown_with_traces():
    summaries = [
        {
            "trace_id": "abcd1234",
            "question": "test q",
            "model": "gpt-4o-mini",
            "latency_ms": 100.0,
            "prompt_tokens": 50,
            "completion_tokens": 10,
            "slowest_span": "rag_generation",
            "slowest_ms": 80.0,
            "start_time": "2026-04-29",
        }
    ]
    output = render_markdown(summaries, total=1)

    assert "# Phoenix Trace Export" in output
    assert "1 trace(s) captured" in output
    assert "abcd1234" in output
    assert "test q" in output
    assert "gpt-4o-mini" in output
    assert "rag_generation" in output


def test_render_markdown_empty():
    output = render_markdown([], total=0)
    assert "No traces found" in output


# --- render_json ------------------------------------------------------------


def test_render_json_roundtrips():
    summaries = [
        {"trace_id": "abc", "question": "q", "latency_ms": 100.0},
    ]
    parsed = json.loads(render_json(summaries))
    assert parsed == summaries


# --- request-level traces (query_request root) ------------------------------

from src.tracing.trace_export import render_trace_tree  # noqa: E402


def _request_trace(trace_id: str = "abcdef0123456789") -> pd.DataFrame:
    """A `query_request` trace: root + stage spans + one nested LLM call."""
    t0 = pd.Timestamp("2026-11-11 12:00:00")
    ms = lambda n: pd.Timedelta(milliseconds=n)  # noqa: E731

    def span(span_id, name, parent, start, end, **attrs):
        row = {
            "context.trace_id": trace_id,
            "context.span_id": span_id,
            "name": name,
            "parent_id": parent,
            "start_time": t0 + ms(start),
            "end_time": t0 + ms(end),
            "span_kind": attrs.pop("kind", "UNKNOWN"),
            "attributes.input.value": attrs.pop("input", None),
        }
        row.update(attrs)
        return row

    return pd.DataFrame(
        [
            span("r", "query_request", None, 0, 10000, kind="CHAIN",
                 input="How heavy is the Selkirk AMPED S2?",
                 **{"attributes.response": {"model": "gpt-4o-mini", "cached": False}}),
            span("ig", "input_guards", "r", 0, 1000),
            span("cl", "classification", "r", 1000, 3000,
                 **{"attributes.classification": {"query_type": "simple", "model": "gpt-4o-mini"}}),
            span("cc", "ChatCompletion", "cl", 1000, 2990, kind="LLM",
                 **{"attributes.llm.model_name": "gpt-4o-mini",
                    "attributes.llm.token_count.prompt": 150,
                    "attributes.llm.token_count.completion": 30}),
            span("rq", "rag_query", "r", 3000, 7000),
            span("rt", "retrieval", "rq", 3000, 3600, kind="RETRIEVER",
                 **{"attributes.retrieval": {"top_k": 5}}),
            span("gn", "generation", "rq", 3600, 7000,
                 **{"attributes.generation": {"model": "gpt-4o-mini",
                                              "prompt_tokens": 1500, "completion_tokens": 20}}),
            span("og", "output_guards", "r", 7000, 9000),
        ]
    )


def test_summarize_request_trace_uses_full_request_latency_and_slowest_stage():
    [s] = summarize_traces(_request_trace(), last_n=10)
    assert s["latency_ms"] == 10000.0
    assert s["question"] == "How heavy is the Selkirk AMPED S2?"
    assert s["model"] == "gpt-4o-mini"
    assert s["slowest_span"] == "generation"  # 3400 ms, the longest stage
    assert s["slowest_ms"] == 3400.0
    assert s["slowest_pct"] == 34.0
    assert (s["prompt_tokens"], s["completion_tokens"]) == (1500, 20)


def test_render_markdown_shows_slowest_share_for_request_traces():
    md = render_markdown(summarize_traces(_request_trace(), last_n=10), total=1)
    assert "generation | 3400.0 (34.0% of request) |" in md


def test_render_trace_tree_shows_connected_stages():
    md = render_trace_tree(_request_trace(), "abcdef")
    for name in ["query_request", "input_guards", "classification", "ChatCompletion",
                 "rag_query", "retrieval", "generation", "output_guards"]:
        assert f"`{name}`" in md
    assert "Request latency (root span `query_request`): 10,000.0 ms" in md
    assert "query_type=simple → gpt-4o-mini" in md
    assert "gpt-4o-mini, 150 prompt + 30 completion tokens" in md
    assert "Slowest stage: `generation`, 3,400.0 ms = 34.0% of the 10,000.0 ms request." in md
    # The classifier call is nested one level under classification
    lines = md.splitlines()
    cc = next(line for line in lines if "`ChatCompletion`" in line)
    assert cc.startswith("| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└ ")


def test_render_trace_tree_unknown_prefix():
    assert "No trace found" in render_trace_tree(_request_trace(), "zzzz")
