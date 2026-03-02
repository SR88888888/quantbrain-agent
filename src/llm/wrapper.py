import requests as req_lib
import json
import time
import re
from typing import Dict, Any, Optional
from src.core.config import settings
from src.core.logger import log


class LLMWrapper:

    def __init__(self):
        self.base_url = settings.LLM_BASE_URL
        self.model_name = settings.MODEL_NAME
        self.timeout = settings.LLM_TIMEOUT
        self.max_retries = settings.LLM_MAX_RETRIES
        self.retry_delay = settings.LLM_RETRY_DELAY
        self._call_count = 0
        self._error_count = 0

    def generate(
        self,
        prompt: str,
        system: str = None,
        expect_json: bool = False,
        max_tokens: int = 1024,
    ) -> str:
        default_system = "你是专业A股金融分析师。请始终使用中文回答,直接输出结论,不要思考过程。"

        if expect_json:
            prompt = prompt + "\n请严格按JSON格式输出,不要包含其他内容。"

        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = req_lib.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": system or default_system},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                    },
                    timeout=self.timeout,
                )

                self._call_count += 1

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    if expect_json:
                        content = self._clean_json(content)
                    return content

                last_error = f"HTTP {response.status_code}"

            except req_lib.exceptions.Timeout:
                last_error = "超时"
                log.warning(f"LLM超时 (尝试 {attempt + 1}/{self.max_retries})")
            except req_lib.exceptions.ConnectionError:
                last_error = "连接失败"
                log.warning(f"LLM连接失败 (尝试 {attempt + 1}/{self.max_retries})")
            except Exception as e:
                last_error = str(e)
                log.warning(f"LLM异常: {e} (尝试 {attempt + 1}/{self.max_retries})")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        self._error_count += 1
        log.error(f"LLM调用最终失败: {last_error}")
        return ""

    def generate_json(self, prompt: str, system: str = None) -> Dict[str, Any]:
        response = self.generate(prompt, system, expect_json=True)
        if not response:
            return {}

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            parsed = self._extract_json(response)
            if parsed:
                return parsed
            log.warning(f"JSON解析失败: {response[:100]}")
            return {}

    def _clean_json(self, text: str) -> str:
        text = re.sub(r"^```json\s*", "", text.strip())
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _extract_json(self, text: str) -> Optional[Dict]:
        for pattern in [r"\{[^{}]*\}", r"\{.*?\}"]:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        return None

    def get_stats(self) -> Dict[str, Any]:
        total = self._call_count
        return {
            "total_calls": total,
            "error_count": self._error_count,
            "success_rate": (total - self._error_count) / total if total > 0 else 1.0,
        }


llm_wrapper = LLMWrapper()
