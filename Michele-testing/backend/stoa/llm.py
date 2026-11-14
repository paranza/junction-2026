"""Gemini fallback for questions no deterministic template covers.

Cost control: Gemini never sees the image. It gets a compact text table of the
facts our models extracted (~1-3k tokens) and must answer from it, citing ids.
Cheapest capable model by default; override with GEMINI_MODEL.
"""
from __future__ import annotations

import json
import os
import re

MODELS = [os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"), "gemini-3.1-flash-lite", "gemini-3.5-flash"]

SYSTEM = """You are a quantity-takeoff assistant for construction workers reading a floor plan.
You receive FACTS extracted from the drawing by measurement models (rooms with areas in m2,
perimeters in m, detected objects with ids, apartments). Answer ONLY from FACTS.
- Do arithmetic exactly; show the formula briefly.
- If FACTS cannot answer, say what is missing. Never invent objects or numbers.
- Paint and wall tiles cover WALL surface (wall_m2 column: perimeter x ceiling height minus openings), flooring covers floor area.
- Reply in the language of the QUESTION sentence itself, never the language of the room names.
Return JSON: {"answer": short text, "value": number or null, "unit": string or null,
"evidence": [room/object ids used], "explanation": one or two sentences}."""


def compact(facts: dict, takeoff: dict | None = None) -> str:
    scale = facts.get("scale", {})
    value = scale.get("m_per_px")
    lines = [f"scale: {value:.5f} m/px ({scale.get('method', '')})" if value else
             "scale: unknown; do not infer physical lengths, areas or quantities from pixels"]
    ceil = (takeoff or {}).get("assumptions", {}).get("ceiling_height_m", 2.5)
    lines.append(f"ceiling height assumed: {ceil} m")
    lines.append("rooms: id | number | name | category | area_m2 | perimeter_m | wall_m2 | unit | outdoor | objects")
    per = {r["id"]: r for r in (takeoff or {}).get("rooms", [])}
    for r in facts["rooms"]:
        objs = [o["type"] for o in facts["objects"] if o.get("room") == r["id"]]
        cnt = ",".join(f"{t}x{objs.count(t)}" for t in sorted(set(objs)))
        lines.append(f"{r['id']} | {r.get('number')} | {r.get('name')} | {r.get('category')} | {r.get('area_m2')} | "
                     f"{per.get(r['id'], {}).get('perimeter_m')} | {per.get(r['id'], {}).get('wall_m2')} | {r.get('unit')} | {r.get('outdoor')} | {cnt}")
    lines.append("object totals: " + json.dumps(facts["summary"]["objects"]))
    lines.append("apartments: " + json.dumps({u["id"]: u["area_m2"] for u in facts["units"]}))
    if facts.get("warnings"):
        lines.append("warnings: " + "; ".join(facts["warnings"][:5]))
    return "\n".join(lines)


def ask(question: str, facts: dict, takeoff: dict | None = None, history: list | None = None) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return {"answer": "No deterministic rule matched and GEMINI_API_KEY is not set.", "value": None,
                "unit": None, "evidence": [], "explanation": "", "method": "none"}
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    ctx = compact(facts, takeoff)
    convo = "".join(f"Q: {h['q']}\nA: {h['a']}\n" for h in (history or [])[-4:])
    prompt = f"FACTS:\n{ctx}\n\n{convo}QUESTION: {question}"
    last_err = None
    for model in MODELS:
        try:
            r = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0,
                                                   response_mime_type="application/json", max_output_tokens=400))
            txt = r.text or "{}"
            m = re.search(r"\{.*\}", txt, re.S)
            out = json.loads(m.group(0) if m else txt)
            usage = getattr(r, "usage_metadata", None)
            out["method"] = f"gemini ({model}) over extracted facts"
            out["tokens"] = {"in": getattr(usage, "prompt_token_count", None), "out": getattr(usage, "candidates_token_count", None)}
            return out
        except Exception as e:  # try the next model
            last_err = e
    return {"answer": f"Gemini unavailable: {last_err}", "value": None, "unit": None, "evidence": [],
            "explanation": "", "method": "error"}
