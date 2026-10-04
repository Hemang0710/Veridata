import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.llm import MockLLM


@pytest.fixture
def spans():
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    exporter.clear()
    return exporter


def test_generate_emits_model_call_span(spans):
    resp = MockLLM("SELECT 1", model="mock-model", version="mock-1").generate("hi")
    assert resp.text == "SELECT 1"

    span = next(s for s in spans.get_finished_spans() if s.name == "llm.call")
    attrs = span.attributes
    assert attrs["gen_ai.request.model"] == "mock-model"
    assert attrs["veridata.model.version"] == "mock-1"
    assert attrs["gen_ai.usage.input_tokens"] == 10
    assert attrs["gen_ai.usage.output_tokens"] == 5
    assert attrs["veridata.llm.latency_ms"] >= 0
