"""Gemini call + disk cache + 429 retry + scorer. Checked offline against google-genai 3.3.0."""
import hashlib, json, math, pathlib, re
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- 1. Retry with backoff on 429 (and 408/5xx). OFF by default: retry_options=None means one attempt.
client = genai.Client(http_options=types.HttpOptions(
    retry_options=types.HttpRetryOptions(attempts=8, initial_delay=2.0, max_delay=60.0)))


# --- 2. Structured intent from a multilingual question.
class Intent(BaseModel):
    family: Literal["count", "area", "length", "volume", "text"]
    target: str = Field(description="English canonical name of the thing asked about, e.g. door, window, sink, room")
    label_verbatim: str | None = Field(None, description="Room or element label exactly as written in the question, never translated")
    rules: list[str] = Field(default_factory=list, description="Counting rules stated in the question, copied verbatim")


# --- 3. Disk cache keyed by model + prompt + config + image bytes.
CACHE = pathlib.Path(".llm_cache")


def generate(prompt: str, model: str = "gemini-4-hydrogen", image: bytes | None = None,
             mime: str = "image/png", schema: type[BaseModel] | None = None,
             thinking: str = "low", resolution: str = "MEDIA_RESOLUTION_HIGH") -> str:
    key = json.dumps([model, prompt, mime, thinking, resolution,
                      schema and schema.model_json_schema(),
                      image and hashlib.sha256(image).hexdigest()], sort_keys=True)
    path = CACHE / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text())["text"]
    parts = [prompt]
    if image is not None:  # generateContent wants MEDIA_RESOLUTION_*; the SDK only warns on plain "high" and sends it as-is
        parts.append(types.Part.from_bytes(data=image, mime_type=mime, media_resolution=resolution))
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=thinking),
        **({"response_mime_type": "application/json",
            "response_json_schema": schema.model_json_schema()} if schema else {}))
    resp = client.models.generate_content(model=model, contents=parts, config=config)
    text = resp.text
    if not text:  # blocked, or thinking used up max_output_tokens: never cache an empty answer
        raise RuntimeError(f"empty response, finish_reason={resp.candidates and resp.candidates[0].finish_reason}")
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps({"model": model, "prompt": prompt, "text": text}))
    return text


# usage: intent = Intent.model_validate_json(generate(question, schema=Intent))
# (resp.parsed swallows ValidationError and returns None; validating yourself surfaces it)


# --- 4. Scorer: counts exact, area/length/volume within 2% of gold.
def to_number(x) -> float:
    # shortcut: reads the first number, decimal comma ok; breaks on "1 234,5" or "1,234.5", fine for our own outputs
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(x))
    return float(m.group().replace(",", ".")) if m else math.nan


def is_correct(family: str, pred, gold) -> bool:
    p, g = to_number(pred), to_number(gold)
    if family == "count":
        return p == g
    if family in ("area", "length", "volume"):
        return abs(p - g) <= 0.02 * abs(g)  # assumption: tolerance relative to gold, inclusive
    raise ValueError(f"no exact scorer for {family}; use the judge")


def is_heldout(drawing_id: str, pct: int = 20) -> bool:
    # split by drawing, not by question, so held-out drawings are never seen while tuning
    return int(hashlib.sha256(drawing_id.encode()).hexdigest(), 16) % 100 < pct
