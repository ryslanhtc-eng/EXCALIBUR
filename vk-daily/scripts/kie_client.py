"""KIE Market client: gpt-image-2-image-to-image.

Docs: POST https://api.kie.ai/api/v1/jobs/createTask
      GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId=...
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
RECORD_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"
MODEL = "gpt-image-2-image-to-image"


class KieError(RuntimeError):
    pass


def _request(
    url: str,
    *,
    api_key: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "ExcaliburVkDaily/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise KieError(f"KIE HTTP {exc.code}: {body}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KieError(f"KIE non-JSON: {raw[:300]}") from exc
    if not isinstance(parsed, dict):
        raise KieError("KIE response is not an object")
    return parsed


def create_i2i_task(
    api_key: str,
    *,
    prompt: str,
    input_urls: list[str],
    aspect_ratio: str = "3:4",
    resolution: str = "2K",
    background: str = "opaque",
) -> str:
    if not input_urls:
        raise KieError("input_urls is required for image-to-image")
    input_payload: dict[str, Any] = {
        "prompt": prompt,
        "input_urls": input_urls,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    # `background` is documented as 1K-only.
    if resolution == "1K" and background:
        input_payload["background"] = background
    payload = {"model": MODEL, "input": input_payload}
    parsed = _request(CREATE_URL, api_key=api_key, method="POST", payload=payload, timeout=60)
    code = parsed.get("code", 200)
    if code not in (200, "200", 0, "0"):
        raise KieError(f"KIE createTask failed: {parsed.get('msg') or parsed}")
    data = parsed.get("data") or {}
    task_id = str(data.get("taskId") or "").strip()
    if not task_id:
        raise KieError(f"KIE createTask missing taskId: {parsed}")
    return task_id


def get_task(api_key: str, task_id: str) -> dict[str, Any]:
    url = RECORD_URL + "?" + urllib.parse.urlencode({"taskId": task_id})
    parsed = _request(url, api_key=api_key, method="GET", timeout=30)
    data = parsed.get("data")
    if not isinstance(data, dict):
        raise KieError(f"KIE recordInfo missing data: {parsed.get('msg') or parsed}")
    return data


def result_urls(task: dict[str, Any]) -> list[str]:
    raw = task.get("resultJson") or ""
    if not raw:
        return []
    if isinstance(raw, dict):
        payload = raw
    else:
        payload = json.loads(raw)
    urls = payload.get("resultUrls") or []
    return [u for u in urls if isinstance(u, str) and u.startswith("https://")]


def wait_for_success(
    api_key: str,
    task_id: str,
    *,
    timeout_s: int = 600,
    poll_s: float = 3.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    delay = poll_s
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last = get_task(api_key, task_id)
        state = str(last.get("state") or "").lower()
        if state == "success":
            return last
        if state == "fail":
            raise KieError(f"KIE task failed: {last.get('failCode')} {last.get('failMsg')}")
        time.sleep(delay)
        delay = min(20.0, delay * 1.3)
    raise KieError(f"KIE task timeout after {timeout_s}s, last={last}")
