"""Gemini detection call (Interactions API, google-genai 3.3.0) returning a validated list of boxes."""
import base64
from typing import Annotated, List

from pydantic import BaseModel, Field


class Box(BaseModel):
    # minItems/maxItems and minimum/maximum are enforced by Gemini constrained decoding (structured-output docs)
    box_2d: List[Annotated[int, Field(ge=0, le=1000)]] = Field(
        min_length=4, max_length=4, description="[ymin, xmin, ymax, xmax] normalized to 0-1000")
    label: str


class Boxes(BaseModel):
    boxes: List[Box]


def request(png_bytes: bytes, what: str, model: str = "gemini-4-hydrogen") -> dict:
    return dict(
        model=model,
        input=[  # docs tip: text before the image
            {"type": "text", "text": (
                f"Detect every {what} in this floor-plan crop, one box per instance, no limit on the "
                "number of boxes. Return an empty list if there are none. "
                "box_2d is [ymin, xmin, ymax, xmax] normalized to 0-1000.")},
            {"type": "image", "data": base64.b64encode(png_bytes).decode(),
             "mime_type": "image/png", "resolution": "high"},
        ],
        response_format={"type": "text", "mime_type": "application/json",
                         "schema": Boxes.model_json_schema()},
        generation_config={"thinking_level": "high"},
    )


def detect(client, png_bytes: bytes, what: str, model: str = "gemini-4-hydrogen") -> List[Box]:
    interaction = client.interactions.create(**request(png_bytes, what, model))
    return Boxes.model_validate_json(interaction.output_text).boxes


if __name__ == "__main__":
    # Offline check only (no API key here): the body must validate against the SDK's own request model.
    from google.genai._gaos.types.interactions.createmodelinteraction import CreateModelInteraction
    body = request(b"\x89PNG fake bytes", "window symbol")
    parsed = CreateModelInteraction.model_validate(body)
    assert parsed.generation_config.thinking_level == "high"
    assert parsed.response_format is not None
    print("request body validates against google-genai CreateModelInteraction")
    print(Boxes.model_json_schema()["$defs"]["Box"]["properties"]["box_2d"])
    print(Boxes.model_validate_json('{"boxes": [{"box_2d": [10, 20, 30, 40], "label": "window"}]}'))
    # Live use: from google import genai; boxes = detect(genai.Client(), open(path, "rb").read(), "window symbol")
