"""Provider-agnostic LLM wrapper (task 4).

Business logic depends on the `LLM` interface, never a vendor SDK. The base
class owns the model-call span so every provider is instrumented identically.
A real provider client is deferred until the API task needs one; `MockLLM` lets
tests run without an API key.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from opentelemetry import trace

tracer = trace.get_tracer("veridata")


@dataclass
class LLMResponse:
    text: str
    model: str
    version: str
    input_tokens: int
    output_tokens: int


class LLM(ABC):
    """Call the model behind a model-call span (GenAI semantic conventions)."""

    def generate(self, prompt: str) -> LLMResponse:
        with tracer.start_as_current_span("llm.call") as span:
            start = time.perf_counter()
            resp = self._generate(prompt)
            latency_ms = (time.perf_counter() - start) * 1000

            span.set_attribute("gen_ai.request.model", resp.model)
            span.set_attribute("gen_ai.response.model", resp.model)
            span.set_attribute("veridata.model.version", resp.version)
            span.set_attribute("gen_ai.usage.input_tokens", resp.input_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", resp.output_tokens)
            span.set_attribute("veridata.llm.latency_ms", latency_ms)
            return resp

    @abstractmethod
    def _generate(self, prompt: str) -> LLMResponse: ...


class MockLLM(LLM):
    """Returns a scripted response; records the last prompt for test assertions."""

    def __init__(
        self,
        text: str,
        model: str = "mock-model",
        version: str = "mock-1",
        input_tokens: int = 10,
        output_tokens: int = 5,
    ) -> None:
        self.text = text
        self.model = model
        self.version = version
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.last_prompt: str | None = None

    def _generate(self, prompt: str) -> LLMResponse:
        self.last_prompt = prompt
        return LLMResponse(
            text=self.text,
            model=self.model,
            version=self.version,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )
