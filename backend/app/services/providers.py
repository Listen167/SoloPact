from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx

from ..config import Settings


class HuaweiOcrProvider:
    name = "huawei-ocr"

    def __init__(self, settings: Settings):
        self.endpoint = (settings.huawei_ocr_endpoint or "").rstrip("/")
        self.token = settings.huawei_ocr_token or ""
        self.project_id = settings.huawei_ocr_project_id or ""

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.token and self.project_id)

    def extract_image(self, image: bytes) -> str:
        if not self.configured:
            return ""
        url = f"{self.endpoint}/v2/{self.project_id}/ocr/general-text"
        response = httpx.post(
            url,
            headers={"X-Auth-Token": self.token, "Content-Type": "application/json"},
            json={"image": base64.b64encode(image).decode("ascii"), "detect_direction": True},
            timeout=30,
        )
        response.raise_for_status()
        blocks = response.json().get("result", {}).get("words_block_list", [])
        return "\n".join(block.get("words", "") for block in blocks if block.get("words"))


class ModelProvider:
    name = "local-template"

    def __init__(self, settings: Settings):
        self.base_url = (settings.model_base_url or "").rstrip("/")
        self.api_key = settings.model_api_key or ""
        self.model = settings.model_name or ""
        if self.configured:
            self.name = "configured-model-api"

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def generate_collection_draft(self, payload: dict[str, Any]) -> dict[str, str] | None:
        if not self.configured:
            return None
        system_prompt = (
            "你是应收款沟通助手。只依据输入事实生成简洁、克制的中文催款草稿，不提供法律意见，"
            "不得添加输入中没有的承诺、罚息或争议信息。仅输出JSON，字段为subject和body。"
        )
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        parsed = json.loads(match.group(0))
        if not isinstance(parsed.get("subject"), str) or not isinstance(parsed.get("body"), str):
            return None
        return {"subject": parsed["subject"], "body": parsed["body"]}
