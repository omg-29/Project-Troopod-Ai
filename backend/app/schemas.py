from typing import Literal, Optional

from pydantic import BaseModel, Field


class TextRequirements(BaseModel):
    """Step 1 output: Extracted keywords and details from user text input."""

    exact_keywords: list[str] = Field(
        description="Exact product, brand, or campaign keywords extracted from the input text."
    )
    specific_details: str = Field(
        description="Concatenated specific requirements including CTA preferences, tone, urgency signals, and segment targeting."
    )


class ImageMetadata(BaseModel):
    """Specific metadata fields extracted from the ad creative."""
    
    color_palette: str = Field(description="Dominant colors or color scheme found in the ad.")
    typography_style: str = Field(description="Fonts, weights, or typographic styling used.")
    brand_name: str = Field(description="The recognizable brand name or logo text.")
    urgency_signals: str = Field(description="Time-sensitive phrases like 'Limited Time' or countdowns.")
    visual_elements: str = Field(description="Other notable visual components, layout, or models used.")


class ImageAnalysis(BaseModel):
    """Step 2 output: Structured analysis of the uploaded ad creative image."""

    main_product: str = Field(
        description="The primary product or service being advertised."
    )
    target_audience: str = Field(
        description="The inferred target audience for this ad creative."
    )
    deal_extracted: str = Field(
        description="Any explicit or implicit deals, offers, discounts, or promotions found in the ad."
    )
    metadata: ImageMetadata = Field(
        description="Additional explicit metadata."
    )


class ScrapedPage(BaseModel):
    """Step 3 output: Everything captured from the target webpage."""

    cleaned_html: str = Field(description="Full cleaned HTML of the target page with absolute URLs.")
    css_bundle: str = Field(description="Concatenated CSS content from inline styles and linked stylesheets.")
    js_bundle: str = Field(description="Concatenated JavaScript content from inline and linked scripts.")
    accessibility_tree: dict = Field(default_factory=dict, description="Accessibility tree snapshot of the page.")
    screenshot_base64: str = Field(description="Base64-encoded full-page PNG screenshot.")
    visual_theme: dict = Field(default_factory=dict, description="Extracted theme info (colors, fonts, variables).")
    base_url: str = Field(description="The resolved base URL of the scraped page.")


# ---------------------------------------------------------------------------
# Step 4 schemas: Structured page modification operations
# ---------------------------------------------------------------------------

class PageOperation(BaseModel):
    """A single surgical modification operation on the landing page."""

    op: Literal[
        "replace_text",     # Replace text content of an element
        "replace_html",     # Replace inner HTML of an element
        "inject_before",    # Insert new HTML before an element
        "inject_after",     # Insert new HTML after an element
        "inject_child",     # Append HTML as last child of an element
        "set_attribute",    # Set/change an attribute on an element
        "add_css",          # Append CSS rules to the page
        "add_js",           # Append JavaScript to the page
    ] = Field(description="The type of DOM operation to perform.")

    selector: Optional[str] = Field(
        default=None,
        description=(
            "CSS selector targeting the element to modify. "
            "Required for all ops except add_css and add_js. "
            "Use simple, robust selectors: IDs (#hero-cta), classes (.main-heading), "
            "or tag-based (h1, .hero-section > h2). Avoid fragile nth-child paths."
        ),
    )

    old_text: Optional[str] = Field(
        default=None,
        description=(
            "For replace_text: the existing text content of the targeted element, "
            "used for verification. Optional but recommended."
        ),
    )

    new_content: str = Field(
        description=(
            "The new value to apply. Meaning depends on op type: "
            "replace_text -> new text string; "
            "replace_html/inject_before/inject_after/inject_child -> HTML snippet; "
            "set_attribute -> attribute value; "
            "add_css -> CSS rules; "
            "add_js -> JavaScript code."
        ),
    )

    attribute_name: Optional[str] = Field(
        default=None,
        description="For set_attribute: the attribute name to set (e.g. 'class', 'style', 'href').",
    )

    justification: str = Field(
        description="One-line CRO justification explaining why this change improves conversion.",
    )


class PageModificationPlan(BaseModel):
    """Complete set of surgical modifications to apply to the landing page."""

    operations: list[PageOperation] = Field(
        description="Ordered list of 5-12 surgical modification operations to apply.",
    )


class ModifiedPage(BaseModel):
    """Step 4 output: The CRO-modified webpage code."""

    html: str = Field(description="Modified HTML source code.")
    css: str = Field(description="Modified or injected CSS.")
    js: str = Field(description="Modified or injected JavaScript.")


class StatusEvent(BaseModel):
    """Server-Sent Event payload for real-time progress updates."""

    stage: str = Field(description="Current pipeline stage identifier.")
    message: str = Field(description="Human-readable status message.")
    progress: int = Field(ge=0, le=100, description="Overall progress percentage.")
    completed: bool = Field(default=False, description="Whether the entire pipeline is complete.")


class GenerationResult(BaseModel):
    """Final response payload containing the modified page."""

    modified_html: str
    modified_css: str
    modified_js: str
    status: str = "success"


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: str
    detail: str
    stage: str = ""
