"""End-to-end RAG flow: retrieve -> prompt -> generate -> respond.

Retrieval and generation each run inside a named OpenTelemetry span
(``retrieval``, ``generation``) so a request trace shows them as labelled
stages, with the auto-instrumented embedding and chat-completion calls
nested underneath. The spans use the OpenTelemetry API directly rather
than ``src.tracing`` (which ranks after ``rag`` in the forward-dependency
order); with no tracer provider configured they are no-ops.
"""

from opentelemetry import trace

from src.config import settings
from src.models import QueryResponse
from src.rag.generator import generate
from src.rag.retriever import retrieve

_tracer = trace.get_tracer(__name__)


def run_pipeline(
    question: str, model: str | None = None, top_k: int = 5
) -> QueryResponse:
    """Run the full RAG pipeline and return a structured QueryResponse."""
    chosen_model = model or settings.model_complex
    with _tracer.start_as_current_span("retrieval") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        span.set_attribute("input.value", question)
        span.set_attribute("retrieval.top_k", top_k)
        sources = retrieve(question, top_k=top_k)
        for i, s in enumerate(sources):
            span.set_attribute(f"retrieval.documents.{i}.document.id", s.doc_id)
            span.set_attribute(f"retrieval.documents.{i}.document.score", s.similarity_score)
    with _tracer.start_as_current_span("generation") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("generation.model", chosen_model)
        answer, usage, cost = generate(question, sources, chosen_model)
        span.set_attribute("generation.prompt_tokens", usage.prompt_tokens)
        span.set_attribute("generation.completion_tokens", usage.completion_tokens)
        span.set_attribute("generation.cost_usd", cost)
        span.set_attribute("output.value", answer)
    confidence = (
        sum(s.similarity_score for s in sources) / len(sources) if sources else 0.0
    )
    return QueryResponse(
        answer=answer,
        sources=sources,
        confidence=confidence,
        model=chosen_model,
        tokens=usage,
        cost_usd=cost,
    )
