"""
Content Optimizer for Troopod CRO Pipeline.

Drastically reduces the size of scraped HTML and CSS before sending to the AI,
stripping out non-visual noise (tracking scripts, analytics, base64 blobs,
comments, duplicate whitespace, third-party widgets) while preserving every
visual element the AI needs to understand and modify the page.
"""

import re
import logging
from bs4 import BeautifulSoup, Comment, Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tags & attributes that are pure noise for CRO analysis
# ---------------------------------------------------------------------------

# Script domains / src patterns that are never relevant to page styling
THIRD_PARTY_SCRIPT_PATTERNS = [
    "google-analytics", "googletagmanager", "gtag", "ga.js", "analytics",
    "facebook", "fbevents", "fbq(", "fb-root",
    "hotjar", "hj(", "clarity", "mouseflow",
    "intercom", "drift", "crisp", "tawk", "zendesk", "livechat", "olark",
    "hubspot", "hs-scripts", "hs-analytics",
    "gtm.js", "gtm.start", "dataLayer", "pixel",
    "onetrust", "cookiebot", "cookie-consent", "cookie-banner",
    "recaptcha", "grecaptcha", "hcaptcha",
    "adsbygoogle", "doubleclick", "googlesyndication",
    "sentry", "bugsnag", "logrocket", "fullstory",
]

# Tags to completely remove (they add no visual value)
REMOVABLE_TAGS = [
    "noscript", "iframe", "object", "embed", "applet",
    # SVGs are often huge icon libraries — the AI has the screenshot
]

# Attributes that bloat HTML but aren't needed for visual understanding
REMOVABLE_ATTRIBUTES = [
    "data-testid", "data-test", "data-cy", "data-qa",
    "data-gtm", "data-analytics", "data-tracking", "data-event",
    "data-react-helmet", "data-reactid", "data-reactroot",
    "data-next", "data-n-head",
    "data-hj", "data-hs",
    "aria-describedby", "aria-labelledby", "aria-controls",
    "tabindex", "role",
    "itemprop", "itemscope", "itemtype",
    "xmlns",
]


def _is_tag_alive(tag) -> bool:
    """Check if a BeautifulSoup tag is still attached to the tree (not decomposed)."""
    return tag is not None and isinstance(tag, Tag) and tag.parent is not None


# ---------------------------------------------------------------------------
# HTML Optimizer
# ---------------------------------------------------------------------------

def optimize_html(html: str, base_url: str = "") -> str:
    """
    Clean and minimize HTML while preserving layout-critical content.

    Removes:
    - HTML comments
    - Third-party/analytics script tags
    - Tracking pixels (1x1 images)
    - Noscript, iframe, SVG (bulk) tags
    - Base64 data URIs in images (replaced with placeholder)
    - Non-visual data-* attributes
    - Excessive whitespace

    Preserves:
    - All text content, headings, paragraphs, buttons
    - Layout structure (divs, sections, headers, footers, nav)
    - Class names and IDs (critical for CSS matching)
    - Image src/alt (non-base64)
    - Form elements
    - Inline styles
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove all HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 2. Remove third-party / analytics script tags
    for script in list(soup.find_all("script")):
        if not _is_tag_alive(script):
            continue
        src = script.get("src", "") or ""
        text = script.string or ""
        combined = (src + text).lower()
        if any(pattern in combined for pattern in THIRD_PARTY_SCRIPT_PATTERNS):
            script.decompose()
            continue
        # Also remove very large inline scripts (>5KB) — likely bundled JS, not content
        if not src and len(text) > 5000:
            script.decompose()

    # 3. Remove noise tags
    for tag_name in REMOVABLE_TAGS:
        for tag in list(soup.find_all(tag_name)):
            if _is_tag_alive(tag):
                tag.decompose()

    # 4. Replace base64 data URIs in images with lightweight placeholders
    for img in list(soup.find_all("img")):
        if not _is_tag_alive(img):
            continue
        src = img.get("src", "") or ""
        if src.startswith("data:"):
            alt = img.get("alt", "image") or "image"
            img["src"] = f"placeholder://{alt}"
        data_src = img.get("data-src", "") or ""
        if data_src.startswith("data:"):
            img["data-src"] = "placeholder://lazy-image"

    # 5. Strip base64 from inline style background-images
    for element in list(soup.find_all(style=True)):
        if not _is_tag_alive(element):
            continue
        style = element.get("style", "") or ""
        if "data:" in style:
            element["style"] = re.sub(
                r"url\(['\"]?data:[^)]+['\"]?\)",
                "url('placeholder://bg')",
                style,
            )

    # 6. Remove non-visual data attributes
    for tag in list(soup.find_all(True)):
        if not _is_tag_alive(tag):
            continue
        attrs_to_remove = []
        for attr in list(tag.attrs.keys()):
            if attr in REMOVABLE_ATTRIBUTES:
                attrs_to_remove.append(attr)
            # Remove all data-* attributes except data-src (lazy loading)
            elif attr.startswith("data-") and attr not in ("data-src", "data-srcset"):
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    # 7. Remove hidden elements (display:none, visibility:hidden)
    for tag in list(soup.find_all(style=True)):
        if not _is_tag_alive(tag):
            continue
        style = (tag.get("style", "") or "").lower()
        if "display:none" in style.replace(" ", "") or "display: none" in style:
            tag.decompose()

    # 8. Remove tracking pixels (tiny images)
    for img in list(soup.find_all("img")):
        if not _is_tag_alive(img):
            continue
        width = img.get("width", "") or ""
        height = img.get("height", "") or ""
        if str(width) in ("0", "1") or str(height) in ("0", "1"):
            img.decompose()

    # 9. Collapse excessive whitespace in the output
    result = str(soup)
    result = re.sub(r"\n\s*\n+", "\n", result)  # Multiple blank lines -> single
    result = re.sub(r"[ \t]+", " ", result)       # Multiple spaces -> single

    return result.strip()


# ---------------------------------------------------------------------------
# CSS Optimizer
# ---------------------------------------------------------------------------

def optimize_css(css: str) -> str:
    """
    Clean and minimize CSS text.

    Removes:
    - CSS comments
    - Duplicate whitespace / blank lines
    - @charset declarations
    - @import rules (already resolved by browser)
    - Source map references
    - Font-face declarations for icon fonts (Font Awesome, Material Icons, etc)
    - Very long base64 data URIs inside CSS

    Preserves:
    - All visual styling rules
    - Media queries
    - Animations / keyframes
    - CSS custom properties (variables)
    """
    if not css or not css.strip():
        return ""

    # 1. Remove CSS comments (/* ... */)
    css = re.sub(r"/\*[\s\S]*?\*/", "", css)

    # 2. Remove source map references
    css = re.sub(r"/\*#\s*sourceMappingURL=.*?\*/", "", css)
    css = re.sub(r"\/\*[@#]\s*sourceURL=.*?\*\/", "", css)

    # 3. Remove @charset declarations
    css = re.sub(r"@charset\s+[^;]+;", "", css, flags=re.IGNORECASE)

    # 4. Remove @import rules
    css = re.sub(r"@import\s+[^;]+;", "", css, flags=re.IGNORECASE)

    # 5. Replace base64 data URIs with placeholders (these can be 100KB+ each)
    css = re.sub(
        r"url\(['\"]?data:[^)]{200,}['\"]?\)",
        "url('placeholder://css-asset')",
        css,
    )

    # 6. Remove icon font @font-face blocks (Font Awesome, Material, etc.)
    icon_font_patterns = [
        r"@font-face\s*\{[^}]*(?:fontawesome|font-awesome|fa-)[^}]*\}",
        r"@font-face\s*\{[^}]*(?:material[- ]icon)[^}]*\}",
        r"@font-face\s*\{[^}]*(?:glyphicon)[^}]*\}",
        r"@font-face\s*\{[^}]*(?:icomoon)[^}]*\}",
    ]
    for pattern in icon_font_patterns:
        css = re.sub(pattern, "", css, flags=re.IGNORECASE)

    # 7. Collapse whitespace
    css = re.sub(r"\n\s*\n+", "\n", css)
    css = re.sub(r"[ \t]+", " ", css)
    # Collapse spaces around CSS syntax
    css = re.sub(r"\s*\{\s*", " { ", css)
    css = re.sub(r"\s*\}\s*", " }\n", css)
    css = re.sub(r"\s*;\s*", "; ", css)

    return css.strip()


# ---------------------------------------------------------------------------
# JS Optimizer
# ---------------------------------------------------------------------------

def optimize_js(js: str) -> str:
    """
    Clean inline JavaScript, removing analytics and tracking code.

    Preserves:
    - DOM manipulation scripts
    - Event listeners for interactive components
    - Animation / scroll behavior scripts
    """
    if not js or not js.strip():
        return ""

    segments = js.split("// --- script boundary ---")
    cleaned_segments = []

    for segment in segments:
        segment_lower = segment.lower()
        # Skip segments that are purely analytics/tracking
        if any(pattern in segment_lower for pattern in THIRD_PARTY_SCRIPT_PATTERNS):
            continue
        # Skip very large scripts (>5KB) — likely bundled app code
        if len(segment.strip()) > 5000:
            continue
        if segment.strip():
            cleaned_segments.append(segment.strip())

    return "\n\n// --- script boundary ---\n\n".join(cleaned_segments)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def optimize_scraped_content(
    html: str,
    css: str,
    js: str,
    base_url: str = "",
) -> tuple[str, str, str]:
    """
    Run full optimization pipeline on scraped page content.

    Returns (optimized_html, optimized_css, optimized_js).

    Gracefully falls back to unoptimized content if any step fails.
    Logs the compression ratio achieved.
    """
    original_total = len(html) + len(css) + len(js)

    # Each optimizer is independently wrapped so one failure doesn't block others
    try:
        opt_html = optimize_html(html, base_url)
    except Exception as e:
        logger.warning("HTML optimization failed, using raw HTML: %s", e)
        opt_html = html

    try:
        opt_css = optimize_css(css)
    except Exception as e:
        logger.warning("CSS optimization failed, using raw CSS: %s", e)
        opt_css = css

    try:
        opt_js = optimize_js(js)
    except Exception as e:
        logger.warning("JS optimization failed, using raw JS: %s", e)
        opt_js = js

    optimized_total = len(opt_html) + len(opt_css) + len(opt_js)

    if original_total > 0:
        ratio = (1 - optimized_total / original_total) * 100
        logger.info(
            "Content optimization: %d chars -> %d chars (%.1f%% reduction) | "
            "HTML: %d->%d | CSS: %d->%d | JS: %d->%d",
            original_total, optimized_total, ratio,
            len(html), len(opt_html),
            len(css), len(opt_css),
            len(js), len(opt_js),
        )

    return opt_html, opt_css, opt_js
