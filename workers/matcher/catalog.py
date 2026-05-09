import json
import os
from dataclasses import dataclass

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")


@dataclass(frozen=True)
class CatalogItem:
    code: str
    category: str
    description: str
    base_price: int
    keywords: tuple[str, ...]


def _load() -> list[CatalogItem]:
    with open(CATALOG_PATH) as f:
        return [
            CatalogItem(
                code=item["code"],
                category=item["category"],
                description=item["description"],
                base_price=item["base_price"],
                keywords=tuple(item["keywords"]),
            )
            for item in json.load(f)
        ]


CATALOG: list[CatalogItem] = _load()


def match(title: str, notes: str) -> tuple[CatalogItem, str]:
    text = f"{title} {notes}".lower()
    fallback = CATALOG[-1]
    best_item = fallback
    best_score = 0
    best_hits: list[str] = []

    for item in CATALOG[:-1]:  # last item is the fallback, skip in scoring
        hits = [kw for kw in item.keywords if kw in text]
        score = len(hits)
        if score > best_score:
            best_score = score
            best_item = item
            best_hits = hits

    if best_score == 0:
        reason = "No specific match found; defaulting to general assessment"
    else:
        reason = f"Matched keywords: {', '.join(best_hits)}"

    return best_item, reason
