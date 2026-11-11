"""One POST /query produces one trace with every pipeline stage connected.

Spans are recorded with a local OpenTelemetry ``TracerProvider`` and an
in-memory exporter, patched into the three modules that create stage
spans. The global tracer provider is never touched, so other tests see
the usual no-op tracing.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.gateway.app import create_app
from src.models import Source, TokenUsage


def _recording_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


def _post(question: str, *, cached=None, hallucination=None):
    tracer, exporter = _recording_tracer()
    sources = [Source(doc_id="prod_001", chunk_text="Selkirk AMPED S2 ... 7.8 oz", similarity_score=0.8)]
    with patch("src.gateway.routes._tracer", tracer), \
         patch("src.gateway.router._tracer", tracer), \
         patch("src.rag.pipeline._tracer", tracer), \
         patch("src.gateway.routes.cache_lookup", return_value=cached), \
         patch("src.gateway.routes.cache_store"), \
         patch("src.gateway.routes.check_hallucination", return_value=hallucination), \
         patch("src.gateway.routes.is_off_topic", return_value=None), \
         patch("src.gateway.router.classify", return_value="simple"), \
         patch("src.gateway.router.log_request"), \
         patch("src.rag.pipeline.retrieve", return_value=sources), \
         patch("src.rag.pipeline.generate",
               return_value=("It weighs 7.8 oz.", TokenUsage(prompt_tokens=100, completion_tokens=8), 0.00002)):
        body = TestClient(create_app()).post("/query", json={"question": question}).json()
    return body, {s.name: s for s in exporter.get_finished_spans()}


def test_query_request_trace_connects_classification_retrieval_and_generation():
    body, spans = _post("How heavy is the Selkirk AMPED S2?")

    for name in ["query_request", "input_guards", "cache_lookup", "classification",
                 "retrieval", "generation", "output_guards", "cache_store"]:
        assert name in spans, f"missing span {name}"

    root = spans["query_request"]
    assert root.parent is None
    # Every recorded span belongs to the same trace as the root
    assert {s.context.trace_id for s in spans.values()} == {root.context.trace_id}
    # Stage spans hang off the request root
    for name in ["input_guards", "cache_lookup", "classification", "output_guards", "cache_store"]:
        assert spans[name].parent.span_id == root.context.span_id
    # Labelled stage attributes
    assert spans["classification"].attributes["classification.query_type"] == "simple"
    assert spans["classification"].attributes["classification.model"] == "gpt-4o-mini"
    assert spans["retrieval"].attributes["retrieval.documents.0.document.id"] == "prod_001"
    assert spans["generation"].attributes["generation.completion_tokens"] == 8
    # The response carries the request-level trace ID
    assert body["trace_id"] == format(root.context.trace_id, "032x")
    assert body["model"] == "gpt-4o-mini"


def test_root_span_records_redacted_question_not_raw_pii():
    _body, spans = _post("My email is jane.doe@example.com. How heavy is the Selkirk AMPED S2?")
    recorded = spans["query_request"].attributes["input.value"]
    assert "jane.doe@example.com" not in recorded
    assert "[REDACTED_EMAIL]" in recorded


def test_blocked_response_still_gets_request_trace_id():
    body, spans = _post("How heavy is the Selkirk AMPED S2?", hallucination="hallucination: made up")
    assert body["blocked_by"] == "hallucination: made up"
    assert body["trace_id"] == format(spans["query_request"].context.trace_id, "032x")
    assert spans["output_guards"].attributes["guard.blocked_by"] == "hallucination: made up"
    assert "cache_store" not in spans
