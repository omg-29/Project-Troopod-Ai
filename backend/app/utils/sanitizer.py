import re


def strip_code_fences(text: str) -> str:
    """
    Remove Markdown code fences from LLM output to extract raw code.

    Handles fences like:
        ```html ... ```
        ```css ... ```
        ```javascript ... ```
        ```js ... ```
        ``` ... ```
    """
    text = text.strip()

    # Pattern: opening fence with optional language tag, content, closing fence
    pattern = r"^```(?:html|css|javascript|js|python|json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If the text starts with ``` but pattern didn't match fully,
    # try line-by-line stripping
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (opening fence)
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Remove last line (closing fence)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    return text


def extract_code_sections(response_text: str) -> dict[str, str]:
    """
    Extract multiple code sections from an LLM response that may contain
    labeled code blocks for HTML, CSS, and JS.

    Returns a dict with keys 'html', 'css', 'js'.
    """
    result = {"html": "", "css": "", "js": ""}

    # Try to find labeled sections
    html_pattern = r"```html\s*\n(.*?)```"
    css_pattern = r"```css\s*\n(.*?)```"
    js_pattern = r"```(?:javascript|js)\s*\n(.*?)```"

    html_match = re.search(html_pattern, response_text, re.DOTALL)
    css_match = re.search(css_pattern, response_text, re.DOTALL)
    js_match = re.search(js_pattern, response_text, re.DOTALL)

    if html_match:
        result["html"] = html_match.group(1).strip()
    if css_match:
        result["css"] = css_match.group(1).strip()
    if js_match:
        result["js"] = js_match.group(1).strip()

    # If no labeled sections found, treat the entire response as HTML
    if not any(result.values()):
        result["html"] = strip_code_fences(response_text)

    return result
