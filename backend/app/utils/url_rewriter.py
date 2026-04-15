from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


REWRITABLE_ATTRIBUTES = [
    ("img", "src"),
    ("img", "data-src"),
    ("img", "srcset"),
    ("script", "src"),
    ("link", "href"),
    ("a", "href"),
    ("source", "src"),
    ("source", "srcset"),
    ("video", "src"),
    ("video", "poster"),
    ("audio", "src"),
    ("iframe", "src"),
    ("form", "action"),
    ("object", "data"),
    ("embed", "src"),
]


def _is_rewritable(value: str) -> bool:
    """Check if a URL value should be rewritten to absolute."""
    if not value or not value.strip():
        return False
    value = value.strip()
    if value.startswith(("data:", "javascript:", "mailto:", "tel:", "#", "blob:")):
        return False
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https", "//"):
        return False
    if value.startswith("//"):
        return False
    return True


def _rewrite_srcset(srcset_value: str, base_url: str) -> str:
    """Rewrite srcset attribute which contains comma-separated URL descriptors."""
    parts = []
    for entry in srcset_value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        tokens = entry.split()
        if tokens and _is_rewritable(tokens[0]):
            tokens[0] = urljoin(base_url, tokens[0])
        parts.append(" ".join(tokens))
    return ", ".join(parts)


def rewrite_css_paths(css: str, base_url: str) -> str:
    """
    Rewrite all url(...) paths in raw CSS text to absolute URLs.
    This is critical for linked stylesheets that use relative paths
    like '../fonts/icon.woff' which break when injected inline.
    """
    if "url(" not in css:
        return css

    import re
    def replace_url(match):
        url = match.group(1).strip("'\" \t\n")
        if _is_rewritable(url):
            return f"url('{urljoin(base_url, url)}')"
        return match.group(0)
        
    return re.sub(r"url\(([^)]+)\)", replace_url, css)


def rewrite_paths(html: str, base_url: str) -> str:
    """
    Parse HTML and rewrite all relative asset paths to absolute URLs.

    Handles src, href, srcset, data-src, action, data, poster attributes
    across all relevant HTML elements. Preserves data URIs, anchors,
    javascript: URIs, and already-absolute URLs.

    Gracefully falls back to original HTML if parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        for tag_name, attr in REWRITABLE_ATTRIBUTES:
            for element in soup.find_all(tag_name):
                value = element.get(attr)
                if value is None:
                    continue

                # Handle list values cleanly (e.g. if BS4 parses as multi-valued)
                if isinstance(value, list):
                    value = " ".join(str(v) for v in value)

                if not isinstance(value, str):
                    continue

                if attr in ("srcset",):
                    element[attr] = _rewrite_srcset(value, base_url)
                elif _is_rewritable(value):
                    element[attr] = urljoin(base_url, value.strip())

        # Handle inline style background-image URLs
        for element in soup.find_all(style=True):
            style = element.get("style") or ""
            if isinstance(style, list):
                style = " ".join(style)
            if "url(" in style:
                element["style"] = rewrite_css_paths(style, base_url)

        return str(soup)

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "URL rewriting failed, using original HTML: %s", e
        )
        return html
