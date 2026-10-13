"""Provider-agnostic LLM wrapper (task 4).

Business logic depends on the `LLM` interface, never a vendor SDK. The base
class owns the model-call span so every provider is instrumented identically.
A real provider client is deferred until the API task needs one; `MockLLM` lets
tests run without an API key.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from opentelemetry import trace

tracer = trace.get_tracer("veridata")

DEFAULT_MODEL = "claude-opus-4-8"


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


class AnthropicLLM(LLM):
    """Real provider. Client is created lazily so the app boots without a key."""

    def __init__(self, model: str | None = None, max_tokens: int = 1024) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self._client = None

    def _generate(self, prompt: str) -> LLMResponse:
        if self._client is None:
            from anthropic import Anthropic  # reads ANTHROPIC_API_KEY from env

            self._client = Anthropic()
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResponse(
            text=text,
            model=resp.model,
            version=resp.model,  # resolved model id is the version we can audit
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
