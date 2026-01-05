import httpx
from typing import List, Dict, Optional
import os
import time
import logging
import asyncio
import json

logger = logging.getLogger(__name__)


class GPTClient:
    """Thin wrapper around a Chat Completions compatible API (like CometAPI) for asynchronous text responses."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        timeout: Optional[int] = 120,
        system_prompt: Optional[str] = None,
    ) -> None:
        # Resolve from environment if not provided
        self.api_key = api_key or os.getenv("COMETAPI_API_KEY") or ""
        self.base_url = (base_url or os.getenv("COMETAPI_BASE_URL") or "https://api.cometapi.com").strip()
        self.model = model or os.getenv("COMETAPI_CHAT_MODEL") or "gpt-4.1"
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(max_tokens)))
        self.timeout = float(os.getenv("OPENAI_TIMEOUT", str(timeout)))
        self.system_prompt = system_prompt or os.getenv("OPENAI_SYSTEM_PROMPT") or "You are a helpful assistant."

        # Retry config
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        self.retry_delay_s = int(os.getenv("OPENAI_RETRY_DELAY_MS", "1000")) / 1000.0
        self.retry_backoff = float(os.getenv("OPENAI_RETRY_BACKOFF", "2"))

        if not self.api_key:
            raise ValueError("COMETAPI_API_KEY is not configured")

    @classmethod
    def from_env(cls) -> "GPTClient":
        return cls()

    def _get_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
            follow_redirects=True,
        )

    async def complete_messages(self, messages: List[Dict[str, any]]) -> str:
        """
        Execute chat completion and return plain text content.
        If messages do not include a system prompt, prepend one from config/env.
        Implements retries with exponential backoff for robustness.
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        endpoint = f"{self.base_url}/v1/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        delay = self.retry_delay_s
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                async with self._get_http_client() as client:
                    logger.info(f"🚀 Starting LLM request to {endpoint} (Attempt {attempt + 1}/{self.max_retries + 1})")
                    resp = await client.post(endpoint, json=body)
                    resp.raise_for_status()

                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content")

                    if content and isinstance(content, str):
                        logger.info(f"✅ LLM request succeeded on attempt {attempt + 1}")
                        return content.strip()
                    
                    last_error = ValueError(f"LLM returned empty or invalid content: {data}")
                    logger.warning(f"⚠️ Empty response on attempt {attempt + 1}, retrying...")

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"⚠️ HTTP Status Error on attempt {attempt + 1}: {e.response.status_code} {e.response.text}"
                )
                # Don't retry on client errors (4xx) except for 429
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    break
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                logger.warning(f"🔌 Connection Error on attempt {attempt + 1}: {type(e).__name__}: {e}")
            except Exception as e:
                last_error = e
                logger.error(f"❌ Unexpected Error on attempt {attempt + 1}: {e}", exc_info=True)
                break 

            if attempt < self.max_retries:
                logger.info(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
                delay *= self.retry_backoff

        error_message = (
            f"ERROR: LLM request failed after {self.max_retries + 1} attempts.\n"
            f"Last error: {type(last_error).__name__}: {last_error}"
        )
        logger.error(error_message)
        return error_message