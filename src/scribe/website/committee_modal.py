"""Locate and narrowly patch committee minute links in MRRA HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser


class CommitteeModalError(ValueError):
    """The requested committee link cannot be identified unambiguously."""


@dataclass(frozen=True)
class AnchorPatch:
    modal_id: str
    label: str
    old_href: str
    new_href: str
    start: int
    end: int

    def apply(self, html: str) -> str:
        return html[: self.start] + self.new_href + html[self.end :]

    @property
    def before(self) -> str:
        return f'<a href="{self.old_href}">…{self.label}…</a>'

    @property
    def after(self) -> str:
        return f'<a href="{self.new_href}">…{self.label}…</a>'


@dataclass
class _Anchor:
    href: str
    href_start: int
    href_end: int
    text: list[str]


class _ModalParser(HTMLParser):
    def __init__(self, html: str, modal_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.html = html
        self.modal_id = modal_id
        self.line_starts = [0]
        self.line_starts.extend(match.end() for match in re.finditer(r"\n", html))
        self.modal_count = 0
        self.modal_depth: int | None = None
        self.depth = 0
        self.anchors: list[_Anchor] = []
        self.active_anchor: _Anchor | None = None

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "div" and attr_map.get("id") == self.modal_id:
            self.modal_count += 1
            if self.modal_depth is None:
                self.modal_depth = self.depth

        inside = self.modal_depth is not None and self.depth > self.modal_depth
        if tag == "a" and inside:
            href = attr_map.get("href")
            if href is not None:
                raw = self.get_starttag_text()
                match = re.search(r"(?i)\bhref\s*=\s*(['\"])(.*?)\1", raw, re.DOTALL)
                if match is None:
                    return
                absolute = self._offset() + match.start(2)
                self.active_anchor = _Anchor(href, absolute, absolute + len(match.group(2)), [])
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth -= 1

    def handle_endtag(self, tag: str) -> None:
        self.depth -= 1
        if tag == "a" and self.active_anchor is not None:
            self.anchors.append(self.active_anchor)
            self.active_anchor = None
        if tag == "div" and self.modal_depth is not None and self.depth == self.modal_depth:
            self.modal_depth = None

    def handle_data(self, data: str) -> None:
        if self.active_anchor is not None:
            self.active_anchor.text.append(data)


def find_anchor_patch(html: str, modal_id: str, label: str, new_href: str) -> AnchorPatch:
    """Validate a modal/month anchor and return an exact href-only patch."""
    parser = _ModalParser(html, modal_id)
    parser.feed(html)
    parser.close()
    if parser.modal_count != 1:
        raise CommitteeModalError(
            f"Expected exactly one modal with id '{modal_id}', found {parser.modal_count}."
        )
    matches = [a for a in parser.anchors if " ".join("".join(a.text).split()) == label]
    if len(matches) != 1:
        raise CommitteeModalError(
            f"Expected exactly one '{label}' month button inside '{modal_id}', found {len(matches)}."
        )
    anchor = matches[0]
    return AnchorPatch(modal_id, label, anchor.href, new_href, anchor.href_start, anchor.href_end)
