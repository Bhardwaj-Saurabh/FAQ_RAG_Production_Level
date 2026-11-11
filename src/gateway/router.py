"""Tiered model routing — classify, dispatch to mini or 4o, log cost.

This is the integration hub: classify → choose model → run traced
pipeline → log per-request cost. Deliverable #3 of the project proposal
(measurable savings from tiered routing) is realised here.
"""

from opentelemetry import trace

from src.config import settings
from src.cost.tracker import log_request
from src.gateway.classifier import QueryType, classify
from src.models import QueryResponse
from src.tracing import traced_pipeline

_tracer = trace.get_tracer(__name__)


def select_model(query_type: QueryType) -> str:
    """Map a query type to the configured model name."""
    return settings.model_simple if query_type == "simple" else settings.model_complex


def route_query(question: str, top_k: int = 5) -> QueryResponse:
    """Full request flow: classify, dispatch, trace, log.

    Classification runs in its own ``classification`` span, a sibling of
    the ``rag_query`` span, so both appear in the caller's request trace.
    """
    with _tracer.start_as_current_span("classification") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("input.value", question)
        query_type = classify(question)
        model = select_model(query_type)
        span.set_attribute("output.value", query_type)
        span.set_attribute("classification.query_type", query_type)
        span.set_attribute("classification.model", model)
    response = traced_pipeline(question, model=model, top_k=top_k)
    log_request(model, response.tokens, response.cost_usd, query_type)
    return response
