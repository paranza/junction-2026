import hashlib, json, os, pathlib
from google import genai
from google.genai import types
from pydantic import BaseModel

client = genai.Client(http_options=types.HttpOptions(
    retry_options=types.HttpRetryOptions(attempts=8, initial_delay=2.0, max_delay=60.0)))
CACHE = pathlib.Path(".llm_cache")

def generate(prompt: str, model: str = "gemini-4-hydrogen", image: bytes | None = None,
             mime: str = "image/png", schema: type[BaseModel] | None = None,
             thinking: str = "low", resolution: str = "MEDIA_RESOLUTION_HIGH") -> str:
    key = json.dumps([model, prompt, mime, thinking, resolution,
                      schema.model_json_schema() if schema else None,
                      hashlib.sha256(image).hexdigest() if image is not None else None], sort_keys=True)
    path = CACHE / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text())["text"]
    parts = [prompt]
    if image is not None:
        parts.append(types.Part.from_bytes(data=image, mime_type=mime, media_resolution=resolution))
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=thinking),
        **({"response_mime_type": "application/json",
            "response_json_schema": schema.model_json_schema()} if schema else {}))
    resp = client.models.generate_content(model=model, contents=parts, config=config)
    reason = resp.candidates[0].finish_reason if resp.candidates else None
    if not resp.text or reason != types.FinishReason.STOP:  # truncated (MAX_TOKENS), blocked or empty: never cache
        raise RuntimeError(f"unusable response, finish_reason={reason}")
    CACHE.mkdir(exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"model": model, "prompt": prompt, "text": resp.text}))
    os.replace(tmp, path)  # atomic: parallel workers never read a half-written file
    return resp.text
