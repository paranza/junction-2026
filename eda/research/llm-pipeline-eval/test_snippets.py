"""Offline check: fake HTTP transport, no network, no API key."""
import json, shutil, time

import httpx2 as httpx  # the SDK ships the httpx2 fork
from google import genai
from google.genai import types

import snippets

calls, bodies = [], []


def handler(request: httpx.Request) -> httpx.Response:
    calls.append(str(request.url))
    bodies.append(json.loads(request.content))
    if len(calls) <= 2:  # two rate-limit errors, then success
        return httpx.Response(429, json={"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    answer = json.dumps({"family": "count", "target": "door", "label_verbatim": "MH", "rules": []})
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": answer}]}}]})


snippets.client = genai.Client(api_key="dummy", http_options=types.HttpOptions(
    retry_options=snippets.client._api_client._http_options.retry_options,  # same retry config as the snippet
    httpx_client=httpx.Client(transport=httpx.MockTransport(handler))))
shutil.rmtree(snippets.CACHE, ignore_errors=True)

t = time.time()
text = snippets.generate("Montako ovea MH:ssa?", image=b"\x89PNGfake", schema=snippets.Intent)
intent = snippets.Intent.model_validate_json(text)
assert intent.label_verbatim == "MH" and intent.family == "count"
assert len(calls) == 3, calls  # retried twice on 429
print(f"retry ok: 3 attempts in {time.time() - t:.1f}s; url={calls[-1]}")

cfg = bodies[-1]["generationConfig"]; print({k: v for k, v in cfg.items() if k != "responseJsonSchema"})
assert cfg["responseMimeType"] == "application/json" and "responseJsonSchema" in cfg
assert "LOW" in cfg["thinkingConfig"].values()  # SDK sends {"thinking_level": "LOW"}; proto JSON takes either case
img = bodies[-1]["contents"][0]["parts"][1]
assert img["mediaResolution"] == {"level": "MEDIA_RESOLUTION_HIGH"} and img["inlineData"]["mime_type"] == "image/png"
print("request body ok:", json.dumps(cfg)[:160])

assert snippets.generate("Montako ovea MH:ssa?", image=b"\x89PNGfake", schema=snippets.Intent) == text
assert len(calls) == 3  # cache hit, no new request
snippets.generate("Montako ovea MH:ssa?", image=b"\x89PNGother", schema=snippets.Intent)
assert len(calls) == 4  # different image bytes -> new key
print("cache ok")

empty = lambda request: httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": []}, "finishReason": "MAX_TOKENS"}]})
snippets.client = genai.Client(api_key="dummy", http_options=types.HttpOptions(httpx_client=httpx.Client(transport=httpx.MockTransport(empty))))
n_files = len(list(snippets.CACHE.glob("*.json")))
try:
    snippets.generate("another question")
    raise AssertionError("empty answer should raise")
except RuntimeError as e:
    print("empty-answer guard ok:", e)
assert len(list(snippets.CACHE.glob("*.json"))) == n_files  # nothing cached

ok = snippets.is_correct
assert ok("count", "3", 3) and ok("count", 3.0, "3") and not ok("count", 2.6, 3)
assert ok("area", "12,25 m2", 12.5) and ok("area", 102.0, 100) and not ok("area", 102.01, 100)
assert ok("area", 98, 100) and not ok("area", 97.99, 100) and ok("length", 0, 0) and not ok("volume", "n/a", 1)
assert snippets.is_heldout("plan_1") == snippets.is_heldout("plan_1")
share = sum(snippets.is_heldout(f"d{i}") for i in range(10000)) / 10000
assert 0.18 < share < 0.22, share
print("scorer + split ok, held-out share", share)
shutil.rmtree(snippets.CACHE, ignore_errors=True)
