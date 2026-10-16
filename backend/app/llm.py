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
# Verification (consistency alt-query + judge) defaults to a cheaper model so
# self-checking does not triple the cost of the primary answer. Override with
# VERIDATA_VERIFY_MODEL.
DEFAULT_VERIFY_MODEL = "claude-haiku-4-5-20251001"


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
    """Returns a scripted response; records the last prompt for test assertions.

    Pass `text` for a single reply returned on every call, or `responses` to
    script a sequence (consumed in order) when one test drives several model
    calls — e.g. the verifier's consistency alt-SQL then the judge verdict.
    """

    def __init__(
        self,
        text: str = "",
        model: str = "mock-model",
        version: str = "mock-1",
        input_tokens: int = 10,
        output_tokens: int = 5,
        responses: list[str] | None = None,
    ) -> None:
        self.text = text
        self._responses = list(responses) if responses is not None else None
        self.model = model
        self.version = version
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.last_prompt: str | None = None

    def _generate(self, prompt: str) -> LLMResponse:
        self.last_prompt = prompt
        if self._responses is not None:
            if not self._responses:
                raise AssertionError("MockLLM(responses=...) exhausted: more calls than scripted")
            text = self._responses.pop(0)
        else:
            text = self.text
        return LLMResponse(
            text=text,
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


class OpenAICompatibleLLM(LLM):
    """Any OpenAI-compatible chat API — Google Gemini, Groq, OpenRouter, etc.

    Config from env: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL. The compat endpoint is
    one POST to {base}/chat/completions, so we use httpx (already a dependency)
    rather than pulling in the openai SDK. Keys are read lazily in _generate so
    the app boots without them.
    """

    def __init__(self, model: str | None = None, max_tokens: int = 1024) -> None:
        self.model = model or os.getenv("LLM_MODEL") or ""
        self.max_tokens = max_tokens

    def _generate(self, prompt: str) -> LLMResponse:
        import httpx

        base_url = (os.getenv("LLM_BASE_URL") or "").rstrip("/")
        api_key = os.getenv("LLM_API_KEY") or ""
        if not (base_url and api_key and self.model):
            raise RuntimeError("OpenAICompatibleLLM needs LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL")
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage") or {}
        resolved = data.get("model") or self.model
        return LLMResponse(
            text=text,
            model=resolved,
            version=resolved,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )


def build_llm(verify: bool = False) -> LLM:
    """Select the provider from LLM_PROVIDER ("anthropic" default, or "openai").

    `verify=True` picks the cheaper verification model: VERIDATA_VERIFY_MODEL if
    set, else the Anthropic haiku default / the primary LLM_MODEL.
    """
    provider = (os.getenv("LLM_PROVIDER") or "anthropic").lower()
    verify_model = os.getenv("VERIDATA_VERIFY_MODEL")
    if provider == "anthropic":
        if verify:
            return AnthropicLLM(model=verify_model or DEFAULT_VERIFY_MODEL)
        return AnthropicLLM()
    if provider in ("openai", "openai_compat", "openai-compatible"):
        return OpenAICompatibleLLM(model=verify_model if verify else None)
    raise ValueError(f"unknown LLM_PROVIDER: {provider!r} (use 'anthropic' or 'openai')")
