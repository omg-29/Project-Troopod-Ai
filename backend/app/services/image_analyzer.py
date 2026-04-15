import logging

from app.schemas import ImageAnalysis
from app.services.ai_client import ai_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert visual ad analyst specializing in digital advertising and conversion rate optimization. Your task is to analyze an uploaded ad campaign creative image and extract structured data from it.

INSTRUCTIONS:
1. Examine every visual element of the image: text overlays, product imagery, colors, typography, branding, logos, and layout.
2. Identify the main product or service being advertised.
3. Infer the target audience based on visual cues, language, and design style.
4. Extract any explicit or implicit deals, offers, discounts, percentages, promo codes, or urgency signals (e.g., "Limited Time", "Ends Soon").
5. Capture metadata about the visual design for style-matching purposes.

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
- "main_product": String identifying the primary product/service.
- "target_audience": String describing the inferred target audience.
- "deal_extracted": String with any deals, offers, or promotions. If none found, write "No explicit deal found".
- "metadata": An object with these string keys: "color_palette", "typography_style", "brand_name", "urgency_signals", "visual_elements", "text_overlays".

EXAMPLE OUTPUT:
{
  "main_product": "Puma Running Shoes - Ultralight Series",
  "target_audience": "Active adults aged 25-40, fitness enthusiasts, runners",
  "deal_extracted": "Buy 1 Get 1 50% Off - Use code RUN50 at checkout",
  "metadata": {
    "color_palette": "Electric blue, white, dark charcoal accents",
    "typography_style": "Bold sans-serif headlines, clean modern body text",
    "brand_name": "CloudFit",
    "urgency_signals": "Limited Time Offer banner, countdown timer visual",
    "visual_elements": "Product hero shot centered, motion blur background, energy lines",
    "text_overlays": "ULTRALIGHT PERFORMANCE | Buy 1 Get 1 50% Off | Code: RUN50 | Shop Now"
  }
}

RULES:
- Return ONLY the JSON object, no markdown fences, no explanation.
- Be thorough in extracting ALL text visible in the image.
- If you cannot identify something clearly, make your best inference and note uncertainty in the value.
- The metadata fields must all be present even if values are minimal."""


async def analyze_image(image_bytes: bytes, mime_type: str) -> ImageAnalysis:
    """
    Step 2: Analyze the uploaded ad creative image using Gemini Vision
    to extract product info, audience, deals, and visual metadata.
    """
    logger.info("Step 2: Analyzing ad creative image (%s)", mime_type)

    result = await ai_client.generate_structured(
        prompt=SYSTEM_PROMPT,
        schema=ImageAnalysis,
        image_bytes=image_bytes,
        mime_type=mime_type,
    )

    logger.info("Step 2 complete: Product identified as '%s'", result.main_product)
    return result
