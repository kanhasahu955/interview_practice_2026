from __future__ import annotations

from functools import lru_cache
from html import escape

import bleach
from markdown_it import MarkdownIt
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexers.special import TextLexer

_ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union(
    {
        "p",
        "pre",
        "code",
        "span",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "blockquote",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "ul",
        "ol",
        "li",
    }
)
_ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "*": ["class"],
    "a": ["href", "title", "rel", "target"],
    "code": ["class"],
    "pre": ["class"],
    "span": ["class"],
    "div": ["class"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}


def _highlight_code(code: str, language: str) -> str:
    lexer = TextLexer()
    lang = (language or "").strip()
    if lang:
        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            lexer = TextLexer()
    else:
        try:
            lexer = guess_lexer(code)
        except Exception:
            lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=False, cssclass="codehilite")
    return highlight(code, lexer, formatter)


@lru_cache
def _markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": True})
    md.enable("table")
    md.enable("strikethrough")

    def fence_renderer(tokens, idx, _options, _env):
        token = tokens[idx]
        info = token.info.strip().split(maxsplit=1)
        language = info[0] if info else ""
        return f'<div class="code-block">{_highlight_code(token.content, language)}</div>'

    def code_block_renderer(tokens, idx, _options, _env):
        token = tokens[idx]
        return (
            '<div class="code-block"><pre class="codehilite"><code>'
            f"{escape(token.content)}</code></pre></div>"
        )

    md.renderer.rules["fence"] = fence_renderer
    md.renderer.rules["code_block"] = code_block_renderer
    return md


def render_markdown(value: str | None) -> Markup:
    raw_html = _markdown().render(value or "")
    clean_html = bleach.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        strip=True,
    )
    linkified_html = bleach.linkify(clean_html)
    return Markup(linkified_html)


def pygments_css() -> str:
    return HtmlFormatter(cssclass="codehilite").get_style_defs(".codehilite")
