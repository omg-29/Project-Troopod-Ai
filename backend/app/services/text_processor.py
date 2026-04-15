import logging

from app.schemas import TextRequirements
from app.services.ai_client import ai_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert CRO (Conversion Rate Optimization) analyst. Your task is to extract structured requirements from a user's plain-text description of their ad campaign and landing page modification needs.

INSTRUCTIONS:
1. Read the user's text carefully.
2. Extract all exact product names, brand names, target audience details, campaign keywords, and key terms.
3. Summarize the specific requirements: what CTA text they want, the tone (urgent, friendly, professional), any specific banners or segments to inject, targeting details, and any constraints.

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
- "exact_keywords": An array of strings. Each string is an exact keyword, product name, or brand term found in the text.
- "specific_details": A single string summarizing all specific CRO requirements, CTA preferences, tone, urgency signals, segment targeting, and any visual/layout instructions.

EXAMPLE INPUT:
"We are running a back-to-college sale campaign for our Gaming Laptop Series 'X'. The ad targets college students aged 16-24. We want the landing page hero to emphasize 'up to 40% off with student discount' with an urgent CTA like 'Claim Your Discount Today'. Tone should be professional but warm."

EXAMPLE OUTPUT:
{
  "exact_keywords": ["Series 'X'", "Gaming Laptops", "Back to College", "40% off", "student discount", "college students"],
  "specific_details": "Campaign promotes Gaming Laptop Series 'X' with a back-to-college sale. Target audience is college students aged 16-24. Hero section should emphasize 'up to 40% off with student discount'. CTA text should read 'Claim Your Discount Today' or similar urgent phrasing. Tone must be professional but warm. Focus on urgency signals related to limited-time offer."
}

RULES:
- Return ONLY the JSON object, no markdown fences, no explanation.
- Include ALL relevant keywords, do not omit any product or brand names.
- The specific_details field should be comprehensive yet concise."""


async def process_text(user_text: str) -> TextRequirements:
    """
    Step 1: Process user's plain text requirements through Gemini
    to extract structured keyword and detail data.
    """
    logger.info("Step 1: Processing text requirements")

    prompt = f"{SYSTEM_PROMPT}\n\nUSER INPUT:\n{user_text}"

    result = await ai_client.generate_structured(
        prompt=prompt,
        schema=TextRequirements,
    )

    logger.info(
        "Step 1 complete: Extracted %d keywords", len(result.exact_keywords)
    )
    return result
