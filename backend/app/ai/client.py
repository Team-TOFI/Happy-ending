"""OpenAI-compatible COPA gateway boundary; no secret or raw response in errors."""

import json

import httpx
from pydantic import ValidationError

from .config import AISettings
from .prompts import PROMPTS


class AIUnavailable(Exception):
    pass


class AIInvalidResponse(Exception):
    pass


class AIClient:
    def __init__(self, settings: AISettings, *, transport=None):
        self.settings = settings
        self.model = settings.model
        self.transport = transport

    def generate(self, stage, payload, schema):
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": PROMPTS[stage]
                    + "\nJSON schema:\n"
                    + json.dumps(schema.model_json_schema(), ensure_ascii=False),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        try:
            with httpx.Client(
                timeout=self.settings.timeout_seconds,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                response = client.post(
                    self.settings.base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": "Bearer " + self.settings.api_key.get_secret_value()},
                    json=body,
                )
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
            raise AIUnavailable("AI 게이트웨이 호출에 실패했습니다") from error
        try:
            envelope = response.json()
            choice = envelope["choices"][0]
            if choice.get("finish_reason") not in (None, "stop"):
                raise ValueError("완성되지 않은 응답")
            content = choice["message"]["content"]
            return schema.model_validate_json(content)
        except (
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            ValueError,
            ValidationError,
        ) as error:
            raise AIInvalidResponse("AI 응답 형식이 올바르지 않습니다") from error
