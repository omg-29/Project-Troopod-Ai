import json
import logging

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


async def repair_json(broken_json: str) -> str:
    """
    Attempt to repair invalid JSON by sending it to Gemini with a repair prompt.
    One retry attempt before raising an error.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    repair_prompt = (
        "The following string was intended to be valid JSON but contains errors. "
        "Fix the JSON syntax errors and return ONLY the corrected, valid JSON. "
        "Do not wrap it in markdown code fences. Do not add any explanation. "
        "Return nothing but the raw fixed JSON.\n\n"
        f"Broken JSON:\n{broken_json}"
    )

    try:
        response = client.models.generate_content(
            model=settings.PRIMARY_MODEL,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        repaired = response.text.strip()
        # Strip markdown fences if present
        if repaired.startswith("```"):
            lines = repaired.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            repaired = "\n".join(lines)

        json.loads(repaired)
        return repaired

    except (json.JSONDecodeError, Exception) as exc:
        logger.error("JSON repair failed: %s", exc)
        raise ValueError(f"JSON repair failed after retry: {exc}") from exc


def validate_and_parse_json(raw: str) -> dict:
    """
    Attempt to parse JSON string. If it fails, perform basic cleanup
    before raising for async repair.
    """
    raw = raw.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try fixing common issues: trailing commas
    import re
    cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON after basic cleanup: {exc}") from exc
