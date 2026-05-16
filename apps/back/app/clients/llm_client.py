from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class LlmServiceError(Exception):
    pass


class LlmClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.llm_base_url or "").rstrip("/")
        self._timeout = timeout_seconds or settings.llm_timeout_seconds

    @property
    def enabled(self) -> bool:
        return settings.llm_enabled and bool(self._base_url)

    async def fetch_score(self, url: str) -> dict[str, Any]:
        if not self.enabled:
            raise LlmServiceError("LLM service is not configured")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/agent/score",
                json={"url": url},
            )
            response.raise_for_status()
            return response.json()

    async def fetch_explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise LlmServiceError("LLM service is not configured")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/agent/explain",
                json=payload,
            )
            response.raise_for_status()
            return response.json()


def get_llm_client() -> LlmClient:
    return LlmClient()
