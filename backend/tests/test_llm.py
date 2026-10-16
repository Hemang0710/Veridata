import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.llm import AnthropicLLM, MockLLM, OpenAICompatibleLLM, build_llm


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


def test_build_llm_selects_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(build_llm(), AnthropicLLM)  # default

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "x")
    assert isinstance(build_llm(), OpenAICompatibleLLM)

    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    with pytest.raises(ValueError):
        build_llm()


def test_openai_compatible_parses_response(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_API_KEY", "k")

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "model": "gemini-2.0-flash",
                "choices": [{"message": {"content": "SELECT 1"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }

    captured = {}

    def _fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _FakeResp()

    import httpx

    monkeypatch.setattr(httpx, "post", _fake_post)

    resp = OpenAICompatibleLLM(model="gemini-2.0-flash").generate("hi")
    assert resp.text == "SELECT 1"
    assert resp.model == "gemini-2.0-flash"
    assert (resp.input_tokens, resp.output_tokens) == (7, 3)
    assert captured["url"] == "https://example.test/v1/chat/completions"  # trailing slash trimmed
    assert captured["kwargs"]["headers"]["Authorization"] == "Bearer k"
