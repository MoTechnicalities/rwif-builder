from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..config.schema import SourceConfig
from ..normalize.records import SourceDocument
from ..utils.hashing import sha256_text

_SUPPORTED_SUFFIXES = {".md": "markdown", ".txt": "text"}


def load_documents(source_configs: list[SourceConfig]) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    seen_paths: set[Path] = set()
    for source in source_configs:
        root = Path(source.path)
        if not root.exists():
            raise ValueError(f"source path does not exist: {root}")
        if root.is_file():
            candidates = [root]
            base_dir = root.parent
        else:
            patterns = source.include or ["**/*.md", "**/*.txt"]
            candidates = list(_iter_matches(root, patterns))
            base_dir = root
        for candidate in sorted(candidates):
            if candidate in seen_paths or not candidate.is_file():
                continue
            source_type = _resolve_source_type(candidate, source.type)
            if source_type is None:
                continue
            seen_paths.add(candidate)
            text = candidate.read_text(encoding="utf-8")
            modified_at = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            documents.append(
                SourceDocument(
                    source_path=candidate,
                    relative_path=candidate.relative_to(base_dir).as_posix() if candidate != base_dir else candidate.name,
                    source_type=source_type,
                    text=text,
                    sha256=sha256_text(text),
                    modified_at=modified_at,
                    metadata={"root": str(base_dir)},
                )
            )
    if not documents:
        raise ValueError("no supported Markdown or text sources were found")
    return documents


def _iter_matches(root: Path, patterns: Iterable[str]) -> Iterable[Path]:
    for pattern in patterns:
        yield from root.glob(pattern)


def _resolve_source_type(path: Path, configured_type: str | None) -> str | None:
    if configured_type is not None:
        normalized = configured_type.strip().lower()
        if normalized in {"markdown", "md"}:
            return "markdown"
        if normalized in {"text", "txt"}:
            return "text"
        raise ValueError(f"unsupported source type for MVP: {configured_type}")
    return _SUPPORTED_SUFFIXES.get(path.suffix.lower())
