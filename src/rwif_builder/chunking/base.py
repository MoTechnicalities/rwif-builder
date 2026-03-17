from __future__ import annotations

import re
from typing import Iterable

from ..normalize.records import ChunkRecord
from ..normalize.records import SourceDocument
from ..utils.hashing import sha256_text

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_WORD_RE = re.compile(r"\S+")


def chunk_document(document: SourceDocument, *, max_tokens: int, overlap_tokens: int) -> list[ChunkRecord]:
    if document.source_type == "markdown":
        return _chunk_markdown(document, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    if document.source_type == "text":
        return _chunk_text(document, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    raise ValueError(f"unsupported source type: {document.source_type}")


def _chunk_markdown(document: SourceDocument, *, max_tokens: int, overlap_tokens: int) -> list[ChunkRecord]:
    sections = _markdown_sections(document.text)
    chunks: list[ChunkRecord] = []
    for section_index, (title, locator, body) in enumerate(sections):
        for window_index, chunk_text in enumerate(_window_text(body, max_tokens=max_tokens, overlap_tokens=overlap_tokens)):
            chunk_id = _chunk_id(document.relative_path, locator, section_index, window_index, chunk_text)
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    memory_id=f"chunk-{chunk_id[:16]}",
                    source_document=document,
                    title=title,
                    canonical_text=chunk_text,
                    locator=f"{locator}#chunk-{window_index + 1}",
                    tags=("markdown",),
                    metadata={"section_index": section_index, "window_index": window_index},
                )
            )
    return chunks


def _chunk_text(document: SourceDocument, *, max_tokens: int, overlap_tokens: int) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    title = document.source_path.stem.replace("_", " ").replace("-", " ").strip() or document.relative_path
    for window_index, chunk_text in enumerate(_window_text(document.text, max_tokens=max_tokens, overlap_tokens=overlap_tokens)):
        locator = f"text#chunk-{window_index + 1}"
        chunk_id = _chunk_id(document.relative_path, locator, 0, window_index, chunk_text)
        chunks.append(
            ChunkRecord(
                chunk_id=chunk_id,
                memory_id=f"chunk-{chunk_id[:16]}",
                source_document=document,
                title=title,
                canonical_text=chunk_text,
                locator=locator,
                tags=("text",),
                metadata={"window_index": window_index},
            )
        )
    return chunks


def _markdown_sections(text: str) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    current_title = "Document"
    current_locator = "document"
    buffer: list[str] = []
    heading_stack: list[tuple[int, str]] = []

    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            content = "\n".join(buffer).strip()
            if content:
                sections.append((current_title, current_locator, content))
            level = len(match.group(1))
            title = match.group(2).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_title = title
            current_locator = " / ".join(item[1] for item in heading_stack)
            buffer = []
            continue
        buffer.append(line)

    content = "\n".join(buffer).strip()
    if content:
        sections.append((current_title, current_locator, content))
    if not sections and text.strip():
        sections.append((current_title, current_locator, text.strip()))
    return sections


def _window_text(text: str, *, max_tokens: int, overlap_tokens: int) -> Iterable[str]:
    tokens = _WORD_RE.findall(text)
    if not tokens:
        return []
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    step = max(1, max_tokens - max(0, overlap_tokens))
    windows: list[str] = []
    start = 0
    while start < len(tokens):
        chunk_tokens = tokens[start : start + max_tokens]
        windows.append(" ".join(chunk_tokens).strip())
        if start + max_tokens >= len(tokens):
            break
        start += step
    return windows


def _chunk_id(relative_path: str, locator: str, section_index: int, window_index: int, chunk_text: str) -> str:
    return sha256_text(f"{relative_path}\n{locator}\n{section_index}\n{window_index}\n{chunk_text}")
