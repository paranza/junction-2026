import sys
sys.path.insert(0, sys.argv[1])
from gemini_detect import request, Box
from google.genai._gaos.types.interactions.createmodelinteraction import CreateModelInteraction
from google.genai._gaos.types.interactions import mediaresolution, thinkinglevel
import typing, pydantic
p = CreateModelInteraction.model_validate(request(b"\x89PNG fake", "window symbol"))
img = p.input[1]
print("image item:", type(img).__name__, getattr(img, "resolution", None), getattr(img, "mime_type", None))
print("response_format:", type(p.response_format).__name__, p.response_format)
print("MediaResolution:", typing.get_args(mediaresolution.MediaResolution) or list(mediaresolution.MediaResolution))
print("ThinkingLevel:", typing.get_args(thinkinglevel.ThinkingLevel) or list(thinkinglevel.ThinkingLevel))
# bad resolution / thinking level must be rejected by the SDK model
for bad in [dict(res="ultra"), dict(tl="minimal_x")]:
    body = request(b"x", "door")
    if "res" in bad: body["input"][1]["resolution"] = bad["res"]
    else: body["generation_config"]["thinking_level"] = bad["tl"]
    try:
        q = CreateModelInteraction.model_validate(body); print("ACCEPTED bad", bad, type(q.input[1]).__name__)
    except pydantic.ValidationError as e:
        print("rejected bad", bad)
try:
    Box.model_validate({"box_2d": [1, 2, 3], "label": "w"}); print("3-coord box ACCEPTED")
except pydantic.ValidationError:
    print("3-coord box rejected")
