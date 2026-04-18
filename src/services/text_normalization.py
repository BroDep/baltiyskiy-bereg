from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET


TAG_BREAK_RE = re.compile(r"<(?:br|/p|/div|/tr|/h\d)\s*/?>", re.IGNORECASE)
TAG_LIST_ITEM_RE = re.compile(r"<li[^>]*>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"[ \t\f\v]+")
MULTINEWLINE_RE = re.compile(r"\n{3,}")


def collapse_whitespace(text: str) -> str:
    normalized = text.replace("\r", "\n")
    normalized = MULTISPACE_RE.sub(" ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = MULTINEWLINE_RE.sub("\n\n", normalized)
    return normalized.strip()


def cleanup_html(raw: str | None) -> str:
    if not raw:
        return ""

    text = raw.replace("&nbsp;", " ")
    text = TAG_BREAK_RE.sub("\n", text)
    text = TAG_LIST_ITEM_RE.sub("- ", text)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return collapse_whitespace(text)


def extract_ru_xml_value(raw: str | None) -> str:
    if not raw:
        return ""

    candidate = raw.strip()
    if not candidate.startswith("<"):
        return collapse_whitespace(candidate)

    try:
        root = ET.fromstring(candidate)
    except ET.ParseError:
        return cleanup_html(candidate)

    for element in root.iter():
        tag_name = element.tag.split("}")[-1].lower()
        text_value = collapse_whitespace(" ".join(element.itertext()))
        if not text_value:
            continue

        if tag_name == "ru":
            return text_value

        language = (
            element.attrib.get("lang")
            or element.attrib.get("Lang")
            or element.attrib.get("culture")
            or element.attrib.get("Culture")
            or ""
        ).lower()
        if language.startswith("ru"):
            return text_value

    return collapse_whitespace(" ".join(root.itertext()))


def normalize_lookup_value(raw: str | None) -> str:
    value = extract_ru_xml_value(raw)
    return cleanup_html(value) if "<" in value else value


def trim_text(text: str, max_chars: int) -> str:
    stripped = collapse_whitespace(text)
    if len(stripped) <= max_chars:
        return stripped
    return stripped[: max_chars - 3].rstrip() + "..."


def build_excerpt(text: str, max_chars: int = 280) -> str:
    return trim_text(text, max_chars)


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    normalized = collapse_whitespace(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + max_chars)
        if end < len(normalized):
            split_at = normalized.rfind("\n", start, end)
            if split_at == -1:
                split_at = normalized.rfind(" ", start, end)
            if split_at > start + max_chars // 2:
                end = split_at

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(normalized):
            break

        start = max(0, end - overlap_chars)

    return chunks


def make_point_id(source_type: str, source_id: int, chunk_index: int = 0) -> str:
    return f"{source_type}:{source_id}:{chunk_index}"


def make_content_hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\n")
    return digest.hexdigest()
