import logging
import base64
from typing import Optional, Type

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.utils.json_repair import repair_json, validate_and_parse_json

logger = logging.getLogger(__name__)


class AIClient:
    """
    Shared Gemini AI client with automatic fallback and JSON repair.

    Primary model: gemini-2.5-flash
    Fallback model: gemini-2.5-flash-lite
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.primary_model = settings.PRIMARY_MODEL
        self.fallback_model = settings.FALLBACK_MODEL

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> BaseModel:
        """
        Generate structured JSON output conforming to a Pydantic schema.

        Attempts primary model first, falls back to secondary on failure.
        If JSON is invalid, attempts repair via dedicated repair prompt.
        """
        contents = self._build_contents(prompt, image_bytes, mime_type)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
        )

        primary_err_msg = ""
        # Attempt 1: Primary model with 2 retries for 503/429 (escalating delays)
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.primary_model,
                    contents=contents,
                    config=config,
                )
                parsed = response.parsed
                if parsed is not None:
                    return parsed
                return await self._manual_parse(response.text, schema)
    
            except Exception as primary_err:
                primary_err_msg = str(primary_err)
                if "503" in primary_err_msg or "429" in primary_err_msg:
                    delay = [8, 15, 25][attempt]
                    logger.warning("Primary model structured 503/429. Retry %d in %ds...", attempt + 1, delay)
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                break

        logger.warning(
            "Primary model (%s) failed: %s. Trying fallback.",
            self.primary_model,
            primary_err_msg,
        )

        # Attempt 2: Fallback model with 2 retries
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.fallback_model,
                    contents=contents,
                    config=config,
                )
                parsed = response.parsed
                if parsed is not None:
                    return parsed
                return await self._manual_parse(response.text, schema)
    
            except Exception as fallback_err:
                if "503" in str(fallback_err) or "429" in str(fallback_err):
                    delay = [8, 15, 25][attempt]
                    logger.warning("Fallback model structured 503/429. Retry %d in %ds...", attempt + 1, delay)
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    "Fallback model (%s) also failed: %s",
                    self.fallback_model,
                    fallback_err,
                )
                raise RuntimeError(
                    f"Both AI models failed. Primary: {primary_err_msg}, Fallback: {fallback_err}"
                ) from fallback_err
        
        raise RuntimeError("Structured generation failed due to persistent capacity errors.")

    async def generate_text(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate freeform text output (for prompt enhancement and code modification).

        Attempts primary model first, falls back to secondary on failure.
        """
        contents = self._build_contents(prompt, image_bytes, mime_type)
        config = types.GenerateContentConfig(temperature=temperature)

        primary_err_msg = ""
        # Attempt 1: Primary model with 2 retries for 503/429 (escalating delays)
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.primary_model,
                    contents=contents,
                    config=config,
                )
                return response.text
    
            except Exception as primary_err:
                primary_err_msg = str(primary_err)
                if "503" in primary_err_msg or "429" in primary_err_msg:
                    delay = [8, 15, 25][attempt]
                    logger.warning("Primary model text 503/429. Retry %d in %ds...", attempt + 1, delay)
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                break
                
        logger.warning(
            "Primary model (%s) text gen failed: %s. Trying fallback.",
            self.primary_model,
            primary_err_msg,
        )

        # Attempt 2: Fallback model with 2 retries
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.fallback_model,
                    contents=contents,
                    config=config,
                )
                return response.text
            except Exception as fallback_err:
                if "503" in str(fallback_err) or "429" in str(fallback_err):
                    delay = [8, 15, 25][attempt]
                    logger.warning("Fallback model text 503/429. Retry %d in %ds...", attempt + 1, delay)
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    "Fallback model (%s) text gen also failed: %s",
                    self.fallback_model,
                    fallback_err,
                )
                raise RuntimeError(
                    f"Both AI models failed for text generation. Primary: {primary_err_msg}, Fallback: {fallback_err}"
                ) from fallback_err
        
        raise RuntimeError("AI models failed due to persistent 503 capacity errors.")

    def _build_contents(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> list:
        """Build the contents list for the Gemini API call."""
        parts = []

        if image_bytes and mime_type:
            parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            )

        parts.append(types.Part.from_text(text=prompt))
        return [types.Content(parts=parts)]

    async def _manual_parse(self, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        """
        Manually parse raw text into the target schema.
        If initial parse fails, attempt JSON repair.
        """
        try:
            data = validate_and_parse_json(raw_text)
            return schema.model_validate(data)
        except (ValueError, Exception) as parse_err:
            logger.warning("Manual parse failed, attempting JSON repair: %s", parse_err)

        # Attempt repair
        repaired_json = await repair_json(raw_text)
        data = validate_and_parse_json(repaired_json)
        return schema.model_validate(data)


# Singleton instance
ai_client = AIClient()
