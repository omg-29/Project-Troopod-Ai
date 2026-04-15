import base64
import logging

from app.schemas import ScrapedPage, ModifiedPage, PageModificationPlan
from app.services.ai_client import ai_client
from app.utils.dom_applicator import apply_operations, build_correction_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite front-end developer and CRO implementation specialist. You receive a "Master Prompt" containing specific, numbered modification instructions, along with the original HTML, CSS, and JS of a landing page, and a screenshot of the page for visual reference.

YOUR TASK:
Return a structured list of surgical modification operations that implement EVERY instruction in the Master Prompt. Do NOT return full HTML — only the specific, targeted changes.

AVAILABLE OPERATION TYPES:
- "replace_text": Replace the text content of an element (use for headings, button labels, paragraphs). Native tags inside the element (like icons or SVGs) will be preserved.
- "replace_html": Replace the inner HTML of an element (use when you need to change structure within an element). 
- "inject_before": Insert new HTML immediately before an element (use for banners above sections).
- "inject_after": Insert new HTML immediately after an element (use for social proof below heroes).
- "inject_child": Append HTML as the last child of an element (add items inside containers).
- "set_attribute": Change an attribute on an element (modify classes, styles, hrefs).
- "add_css": Append new CSS rules to the page (for styling new elements or modifications).
- "add_js": Append new JavaScript to the page (for animations or dynamic behavior).

CSS SELECTOR GUIDELINES:
- Use simple, robust selectors that match the actual DOM structure.
- Prefer IDs (#hero-cta), classes (.main-heading), and tag+class combos (h1.title).
- Use hierarchy when needed: .hero-section > h1, header .nav-cta.
- AVOID fragile selectors like nth-child(3) > div:nth-of-type(2).
- Reference the HTML provided to verify your selectors match real elements.

CRITICAL SAFETY RULES:
1. NEVER target large layout wrappers (e.g., <main>, <div id="root">, <div class="container">) with replace_html or replace_text. Doing so will delete the entire page and result in a blank screen.
2. ALWAYS target the most specific, atomic element possible (e.g., target the <h1> directly, not the wrapper <div> containing the <h1>).
3. If adding a new section (like a banner), use "inject_before" or "inject_after" on a sibling element, rather than trying to replace a parent.

IMPLEMENTATION RULES:
1. For text changes: Use "replace_text" with the exact CSS selector of the target element. 
2. For new elements: Use "inject_before" or "inject_after" with full inline-styled HTML that matches the page's existing design language.
3. For CTA modifications: Use "replace_text" for button labels plus "add_css" for subtle enhancements. Do not replace_html on buttons to avoid deleting their SVG icons.
4. For style changes: Use "add_css" with new rules. Never remove existing critical styles.
5. For urgency elements: Use subtle, professional styling. No flashy animations or jarring colors.
6. DO NOT add any emojis anywhere in the content.
7. DO NOT reference the modification process in any generated content.
8. Every operation MUST include a CRO justification.
9. Aim for 5-12 high-impact operations maximum.

CRITICAL:
- Your selectors MUST match elements that actually exist in the provided HTML.
- The modifications must feel ORGANIC — as if the page was always designed this way."""


async def modify_page(
    master_prompt: str,
    scraped_page: ScrapedPage,
) -> ModifiedPage:
    """
    Step 4b: Web Page Modification Agent.

    Feeds the Master Prompt + scraped HTML/CSS/JS + screenshot to the LLM.
    The LLM returns structured PageOperation objects instead of full HTML.
    Operations are then applied surgically to the original page via BeautifulSoup.

    If >50% of operations fail (bad selectors), triggers a corrective retry
    where failed operations are sent back with HTML context for the AI to fix.
    """
    logger.info("Step 4b: Executing code modification with Master Prompt (diff-based)")

    # Prepare screenshot bytes for visual reference
    screenshot_bytes = None
    if scraped_page.screenshot_base64:
        screenshot_bytes = base64.b64decode(scraped_page.screenshot_base64)

    # Log content sizes for monitoring
    logger.info(
        "Payload sizes -> HTML: %d chars, CSS: %d chars, JS: %d chars",
        len(scraped_page.cleaned_html),
        len(scraped_page.css_bundle),
        len(scraped_page.js_bundle),
    )

    # With diff-based output, we can be much more generous with input limits.
    # The AI output is now ~1-5K tokens (JSON operations) instead of 50-100K+ (full HTML).
    html_limit = 480_000
    css_limit = 400_000
    js_limit = 120_000

    logger.info(
        "Truncating payload -> HTML: %d/%d, CSS: %d/%d, JS: %d/%d",
        min(len(scraped_page.cleaned_html), html_limit), len(scraped_page.cleaned_html),
        min(len(scraped_page.css_bundle), css_limit), len(scraped_page.css_bundle),
        min(len(scraped_page.js_bundle), js_limit), len(scraped_page.js_bundle),
    )

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== MASTER PROMPT (Modification Instructions) ===\n"
        f"{master_prompt}\n\n"
        f"=== ORIGINAL HTML ===\n"
        f"{scraped_page.cleaned_html[:html_limit]}\n\n"
        f"=== ORIGINAL CSS ===\n"
        f"{scraped_page.css_bundle[:css_limit]}\n\n"
        f"=== ORIGINAL JAVASCRIPT ===\n"
        f"{scraped_page.js_bundle[:js_limit]}\n"
    )

    # --- First attempt: get structured operations ---
    plan = await ai_client.generate_structured(
        prompt=prompt,
        schema=PageModificationPlan,
        image_bytes=screenshot_bytes,
        mime_type="image/png" if screenshot_bytes else None,
    )

    logger.info(
        "AI returned %d operations",
        len(plan.operations),
    )

    # --- Apply operations to original HTML ---
    patched_html, apply_result = apply_operations(
        html=scraped_page.cleaned_html,
        operations=plan.operations,
        base_url=scraped_page.base_url,
    )

    # --- Corrective retry if >50% operations failed ---
    if apply_result.failure_rate > 0.5 and len(apply_result.failed) > 0:
        logger.warning(
            "High failure rate (%.0f%%) — %d/%d operations failed. Triggering corrective retry.",
            apply_result.failure_rate * 100,
            len(apply_result.failed),
            apply_result.total,
        )

        correction_context = build_correction_context(
            html=scraped_page.cleaned_html,
            failed_ops=apply_result.failed,
            max_snippet_chars=5000,
        )

        correction_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== CORRECTION TASK ===\n"
            f"Your previous modification attempt had selector failures. "
            f"Fix the selectors so they match actual elements in the HTML.\n\n"
            f"{correction_context}\n\n"
            f"=== FULL HTML FOR REFERENCE ===\n"
            f"{scraped_page.cleaned_html[:html_limit]}\n"
        )

        try:
            corrected_plan = await ai_client.generate_structured(
                prompt=correction_prompt,
                schema=PageModificationPlan,
                image_bytes=screenshot_bytes,
                mime_type="image/png" if screenshot_bytes else None,
            )

            logger.info(
                "Corrective retry returned %d operations",
                len(corrected_plan.operations),
            )

            # Re-apply from scratch with the corrected plan merged with originally successful ops
            # Strategy: start from original HTML, apply all successful ops + corrected ops
            all_operations = [op for _, op in apply_result.succeeded] + corrected_plan.operations

            patched_html, apply_result = apply_operations(
                html=scraped_page.cleaned_html,
                operations=all_operations,
                base_url=scraped_page.base_url,
            )

            logger.info(
                "After correction: %d/%d operations succeeded",
                len(apply_result.succeeded),
                apply_result.total,
            )

        except Exception as correction_err:
            logger.error(
                "Corrective retry failed: %s. Using results from first attempt.",
                correction_err,
            )

    # Collect injected CSS and JS separately for transparency in the response
    css_additions = "\n".join(apply_result.injected_css)
    js_additions = "\n".join(apply_result.injected_js)

    logger.info("Step 4b complete: Modified HTML (%d chars)", len(patched_html))
    return ModifiedPage(html=patched_html, css=css_additions, js=js_additions)
