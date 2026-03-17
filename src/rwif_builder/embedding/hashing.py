from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

import numpy as np

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_'-]+")


@dataclass
class HashingActivationProvider:
    model_id: str = "rwif-hash-v1"
    vector_length: int = 256

    def encode_text(self, text: str) -> np.ndarray:
        return self.encode_texts([text])[0]

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            raise ValueError("texts must not be empty")
        vectors = [self._encode_single(text) for text in texts]
        return np.stack(vectors, axis=0)

    def _encode_single(self, text: str) -> np.ndarray:
        vector = np.zeros(self.vector_length, dtype=np.float64)
        tokens = [token.lower() for token in _TOKEN_RE.findall(text)]
        if not tokens:
            return vector
        for index, token in enumerate(tokens):
            self._accumulate(vector, token, weight=1.0)
            if index + 1 < len(tokens):
                self._accumulate(vector, f"{token}|{tokens[index + 1]}", weight=0.5)
        norm = float(np.linalg.norm(vector))
        if norm > 0.0:
            vector /= norm
        return vector

    def _accumulate(self, vector: np.ndarray, token: str, *, weight: float) -> None:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "little") % self.vector_length
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        scale = 1.0 + (digest[9] / 255.0)
        vector[bucket] += sign * weight * scale
