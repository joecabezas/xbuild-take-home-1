import json
import os
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")
MODEL_NAME = os.environ.get("MATCHER_MODEL", "all-MiniLM-L6-v2")
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.35"))

_model = SentenceTransformer(MODEL_NAME)


@dataclass(frozen=True)
class CatalogItem:
    code: str
    category: str
    description: str
    base_price: int


def _load() -> list[CatalogItem]:
    with open(CATALOG_PATH) as f:
        return [
            CatalogItem(
                code=item["code"],
                category=item["category"],
                description=item["description"],
                base_price=item["base_price"],
            )
            for item in json.load(f)
        ]


CATALOG: list[CatalogItem] = _load()

# Precompute embeddings for all items except the fallback (last item)
_scoreable = CATALOG[:-1]
_catalog_embeddings: np.ndarray = _model.encode(
    [f"{item.code} {item.description}" for item in _scoreable],
    normalize_embeddings=True,
)


def match(title: str, notes: str) -> tuple[CatalogItem, str]:
    fallback = CATALOG[-1]
    query = f"{title} {notes}".strip()
    query_embedding = _model.encode(query, normalize_embeddings=True)

    # Cosine similarity — since both sides are L2-normalized, this is just a dot product
    scores: np.ndarray = _catalog_embeddings @ query_embedding
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score < SIMILARITY_THRESHOLD:
        return fallback, "No specific match found; defaulting to general assessment"

    item = _scoreable[best_idx]
    return item, f"Semantic match (score {best_score:.2f}): {item.description}"
