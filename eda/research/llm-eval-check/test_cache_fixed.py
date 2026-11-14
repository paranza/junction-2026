import json, shutil, sys
import httpx2 as httpx
from google import genai
from google.genai import types
import cache_fixed as m

def mk(handler):
    return genai.Client(api_key="dummy", http_options=types.HttpOptions(httpx_client=httpx.Client(transport=httpx.MockTransport(handler))))
calls = []
def ok(req):
    calls.append(1)
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": '{"a": 1}'}]}, "finishReason": "STOP"}]})
def truncated(req):
    calls.append(1)
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": '{"fam'}]}, "finishReason": "MAX_TOKENS"}]})
shutil.rmtree(m.CACHE, ignore_errors=True)
m.client = mk(truncated)
try:
    m.generate("q1"); raise AssertionError("truncated answer must raise")
except RuntimeError as e:
    print("truncated guard ok:", e)
assert not m.CACHE.exists() or not list(m.CACHE.glob("*.json")), "truncated answer was cached"
m.client = mk(ok)
assert m.generate("q1") == '{"a": 1}' and m.generate("q1") == '{"a": 1}' and len(calls) == 2  # 1 truncated + 1 ok, then cache hit
m.generate("q1", image=b"")  # empty bytes no longer crash json.dumps
assert len(calls) == 3 and not list(m.CACHE.glob("*.tmp"))
print("STOP-only cache, atomic write, empty-bytes key ok;", len(list(m.CACHE.glob('*.json'))), "files")
shutil.rmtree(m.CACHE, ignore_errors=True)
