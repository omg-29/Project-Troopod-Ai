"""
DOM Applicator for Troopod CRO Pipeline.

Applies structured PageOperation objects to the original HTML using BeautifulSoup.
Each operation is surgically applied — the original page is never regenerated,
only patched at specific points. This approach:
  - Guarantees the original page structure is preserved
  - Uses ~1-5K output tokens instead of 50-100K+
  - Makes selector failures recoverable (skip and log)
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag

from app.schemas import PageOperation

logger = logging.getLogger(__name__)


class ApplyResult:
    """Result of applying a batch of operations to an HTML document."""

    def __init__(self):
        self.succeeded: list[tuple[int, PageOperation]] = []
        self.failed: list[tuple[int, PageOperation, str]] = []
        self.injected_css: list[str] = []
        self.injected_js: list[str] = []

    @property
    def total(self) -> int:
        return len(self.succeeded) + len(self.failed)

    @property
    def failure_rate(self) -> float:
        return len(self.failed) / self.total if self.total > 0 else 0.0


def apply_operations(
    html: str,
    operations: list[PageOperation],
    base_url: str,
) -> tuple[str, ApplyResult]:
    """
    Apply a list of PageOperation objects to the original HTML.

    Returns (patched_html, ApplyResult) where patched_html is the complete
    self-contained HTML document with all successful operations applied,
    <base> tag injected, and CSS/JS appended.
    """
    soup = BeautifulSoup(html, "html.parser")
    result = ApplyResult()

    for idx, op in enumerate(operations):
        try:
            _apply_single(soup, op, idx, result)
        except Exception as exc:
            reason = f"Unexpected error: {exc}"
            result.failed.append((idx, op, reason))
            logger.warning(
                "Operation %d (%s) failed: %s | selector=%s",
                idx, op.op, reason, op.selector,
            )

    # Inject <base> tag for asset resolution
    _inject_base_tag(soup, base_url)

    # Inject accumulated CSS before </head>
    if result.injected_css:
        css_text = "\n".join(result.injected_css)
        _inject_css(soup, css_text)

    # Inject accumulated JS before </body>
    if result.injected_js:
        js_text = "\n".join(result.injected_js)
        _inject_js(soup, js_text)

    # Log summary
    logger.info(
        "DOM applicator: %d/%d operations succeeded (%.0f%% failure rate)",
        len(result.succeeded),
        result.total,
        result.failure_rate * 100,
    )

    return str(soup), result


# ---------------------------------------------------------------------------
# Individual operation handlers
# ---------------------------------------------------------------------------

def _apply_single(
    soup: BeautifulSoup,
    op: PageOperation,
    idx: int,
    result: ApplyResult,
) -> None:
    """Apply a single operation to the soup. Mutates soup in place."""

    # Global operations (no selector needed)
    if op.op == "add_css":
        result.injected_css.append(op.new_content)
        result.succeeded.append((idx, op))
        logger.debug("Operation %d: add_css (%d chars)", idx, len(op.new_content))
        return

    if op.op == "add_js":
        result.injected_js.append(op.new_content)
        result.succeeded.append((idx, op))
        logger.debug("Operation %d: add_js (%d chars)", idx, len(op.new_content))
        return

    # Element-targeted operations require a valid selector
    if not op.selector:
        result.failed.append((idx, op, "Missing CSS selector for element-targeted operation"))
        return

    element = soup.select_one(op.selector)
    if element is None:
        result.failed.append((idx, op, f"Selector '{op.selector}' matched no elements"))
        logger.warning("Operation %d (%s): selector '%s' matched nothing", idx, op.op, op.selector)
        return

    if op.op == "replace_text":
        _op_replace_text(element, op)

    elif op.op == "replace_html":
        _op_replace_html(soup, element, op)

    elif op.op == "inject_before":
        _op_inject_before(soup, element, op)

    elif op.op == "inject_after":
        _op_inject_after(soup, element, op)

    elif op.op == "inject_child":
        _op_inject_child(soup, element, op)

    elif op.op == "set_attribute":
        _op_set_attribute(element, op)

    else:
        result.failed.append((idx, op, f"Unknown operation type: {op.op}"))
        return

    result.succeeded.append((idx, op))
    logger.debug(
        "Operation %d: %s on '%s' — %s",
        idx, op.op, op.selector, op.justification[:80],
    )


import bs4

def _op_replace_text(element: Tag, op: PageOperation) -> None:
    """Replace the text content of an element natively, preserving child tags (like icons/SVGs)."""
    # Find all direct navigable strings
    direct_strings = [c for c in element.contents if isinstance(c, bs4.NavigableString)]
    has_meaningful_string = False
    
    for string_node in direct_strings:
        if string_node.strip():
            if not has_meaningful_string:
                string_node.replace_with(op.new_content)
                has_meaningful_string = True
            else:
                string_node.replace_with("") # Clear extra string fragments
                
    # If no direct text was found, look deeper (e.g. inside a nested span like <button><span>Text</span><svg/></button>)
    if not has_meaningful_string:
        deep_strings = element.find_all(string=True, recursive=True)
        # Filter out text inside scripts/styles/svgs
        meaningful_deep = [
            s for s in deep_strings 
            if s.strip() and s.parent and s.parent.name not in ["script", "style", "svg", "noscript"]
        ]
        
        if meaningful_deep:
            meaningful_deep[0].replace_with(op.new_content)
            for s in meaningful_deep[1:]:
                s.replace_with("")
        else:
            # Fallback: just append the text if the tag is completely empty
            element.append(op.new_content)


def _op_replace_html(soup: BeautifulSoup, element: Tag, op: PageOperation) -> None:
    """Replace the inner HTML of an element."""
    element.clear()
    new_content = BeautifulSoup(op.new_content, "html.parser")
    for child in list(new_content.children):
        element.append(child)


def _op_inject_before(soup: BeautifulSoup, element: Tag, op: PageOperation) -> None:
    """Insert new HTML immediately before an element."""
    new_content = BeautifulSoup(op.new_content, "html.parser")
    for child in reversed(list(new_content.children)):
        element.insert_before(child)


def _op_inject_after(soup: BeautifulSoup, element: Tag, op: PageOperation) -> None:
    """Insert new HTML immediately after an element."""
    new_content = BeautifulSoup(op.new_content, "html.parser")
    # insert_after in order — need to insert in reverse to maintain order
    children = list(new_content.children)
    ref = element
    for child in children:
        ref.insert_after(child)
        ref = child


def _op_inject_child(soup: BeautifulSoup, element: Tag, op: PageOperation) -> None:
    """Append HTML as the last child of an element."""
    new_content = BeautifulSoup(op.new_content, "html.parser")
    for child in list(new_content.children):
        element.append(child)


def _op_set_attribute(element: Tag, op: PageOperation) -> None:
    """Set or modify an attribute on an element."""
    if not op.attribute_name:
        raise ValueError("set_attribute requires attribute_name")
    element[op.attribute_name] = op.new_content


# ---------------------------------------------------------------------------
# Page assembly helpers (moved from old code_modifier._combine_page)
# ---------------------------------------------------------------------------

def _inject_base_tag(soup: BeautifulSoup, base_url: str) -> None:
    """Inject a <base> tag for correct asset resolution."""
    base_tag_html = f'<base href="{base_url}/" target="_self">'
    base_tag = BeautifulSoup(base_tag_html, "html.parser").find("base")

    head = soup.find("head")
    if head:
        # Insert at the beginning of <head>
        head.insert(0, base_tag)
    else:
        # Create <head> if missing
        html_tag = soup.find("html")
        if html_tag:
            new_head = soup.new_tag("head")
            new_head.append(base_tag)
            html_tag.insert(0, new_head)
        else:
            new_head = BeautifulSoup(
                f"<html><head>{base_tag_html}</head></html>", "html.parser"
            )
            soup.insert(0, new_head)


def _inject_css(soup: BeautifulSoup, css_text: str) -> None:
    """Inject a <style> block before </head>."""
    style_tag = soup.new_tag("style")
    style_tag.string = f"\n/* Troopod CRO Modifications */\n{css_text}\n"

    head = soup.find("head")
    if head:
        head.append(style_tag)
    else:
        # Prepend to document
        soup.insert(0, style_tag)


def _inject_js(soup: BeautifulSoup, js_text: str) -> None:
    """Inject a <script> block before </body>."""
    script_tag = soup.new_tag("script")
    script_tag.string = f"\n// Troopod CRO Modifications\n{js_text}\n"

    body = soup.find("body")
    if body:
        body.append(script_tag)
    else:
        # Append to end of document
        soup.append(script_tag)


def build_correction_context(
    html: str,
    failed_ops: list[tuple[int, PageOperation, str]],
    max_snippet_chars: int = 2000,
) -> str:
    """
    Build a context string to send back to the AI for correcting failed selectors.

    Includes the failed operations and a trimmed snippet of the HTML to help
    the AI understand the actual DOM structure.
    """
    lines = ["The following operations failed because their CSS selectors did not match any elements.\n"]
    lines.append("Please return a corrected PageModificationPlan with fixed selectors.\n")
    lines.append("--- FAILED OPERATIONS ---\n")

    for idx, op, reason in failed_ops:
        lines.append(
            f"  Operation {idx}: op={op.op}, selector='{op.selector}', "
            f"reason='{reason}', intended: {op.justification}"
        )

    lines.append(f"\n--- HTML STRUCTURE (first {max_snippet_chars} chars) ---\n")
    lines.append(html[:max_snippet_chars])

    return "\n".join(lines)
