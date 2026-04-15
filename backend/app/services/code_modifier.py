import base64
import logging

from app.schemas import ScrapedPage, ModifiedPage, PageModificationPlan
from app.services.ai_client import ai_client
from app.utils.dom_applicator import apply_operations, build_correction_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite front-end developer and CRO implementation specialist. You receive a "Master Prompt" containing specific, numbered modification instructions (6-8 items), along with the original HTML, CSS, and JS of a landing page.

YOUR TASK:
Return a structured list of surgical modification operations that implement EVERY instruction in the Master Prompt. Ensure modifications are bold, visible, and structurally sound.

IMPLEMENTATION & SAFETY RULES:
1. INJECTION FIDELITY: Every "inject_before", "inject_after", or "inject_child" operation that adds a visible HTML element (like a banner or div) MUST include inline styles to guarantee visibility. Specifically, add `display: block !important; opacity: 1 !important; visibility: visible !important; z-index: 9999 !important;` to your new elements. Ensure they have appropriate `background-color` and `padding` matching the brand.
2. TEXT IMPACT: Be bold with "replace_text". If the Master Prompt says to update a headline, update the whole headline. Do not be timid.
3. ORGANIC DESIGN: Use the provided CSS context to pick existing classes when possible, but prioritize visibility. If a font or color is specified in the Master Prompt (from the theme), use it exactly.
4. TARGETING: Use the most specific selector possible (IDs are best). AVOID targeting large layout wrappers (e.g., <main>, <div id="root">) with `replace_html` or `replace_text` to avoid clearing the whole page.
5. DOM PRECISION: For "replace_text", ensure you are targeting a leaf element containing text (h1, h2, p, span, a, button) to avoid deleting nested UI components.
6. NO EMOJIS: Do not include emojis in any generated content.

OPERATION TYPES:
- "replace_text": Replace the text of a specific element (best for headlines, buttons).
- "replace_html": Replace the inner HTML of a container.
- "inject_before/after": Insert new sections (banners, trust bars).
- "add_css": Add global styles (animations, new classes).

CRITICAL: Every instruction in the Master Prompt MUST result in at least one operation. If you fail to implement an instruction, the user will see it as a failure."""


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
