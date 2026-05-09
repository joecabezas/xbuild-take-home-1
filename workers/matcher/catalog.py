from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogItem:
    code: str
    category: str
    description: str
    base_price: int
    keywords: tuple[str, ...]


CATALOG: list[CatalogItem] = [
    CatalogItem("roof.leak_investigation", "roofing",
                "Investigate and stop active leak; seal/repair likely entry points.",
                650, ("leak", "water", "wet", "drip", "seep", "stain")),
    CatalogItem("roof.patch_shingles", "roofing",
                "Replace missing/damaged shingles in affected areas.",
                900, ("shingle", "shingles", "missing", "damaged", "blow", "blown")),
    CatalogItem("roof.reflash_penetration", "roofing",
                "Repair/replace flashing at affected areas to restore watertightness.",
                750, ("flashing", "flash", "penetration", "chimney")),
    CatalogItem("roof.vent_repair", "roofing",
                "Inspect and repair/replace roof vent components as needed.",
                400, ("vent", "ventilation", "soffit")),
    CatalogItem("gutters.clean_flush", "gutters",
                "Clean and flush gutters and downspouts.",
                250, ("gutter", "clog", "clogged", "debris", "leaves", "flush", "downspout")),
    CatalogItem("gutters.resecure", "gutters",
                "Re-secure gutters; adjust hangers and slope for proper drainage.",
                350, ("gutter", "loose", "pulling", "detach", "sag", "sagging", "fascia")),
    CatalogItem("siding.repair_local", "siding",
                "Repair/replace localized siding/trim damage.",
                700, ("siding", "trim", "panel", "board")),
    CatalogItem("openings.reseal", "windows_doors",
                "Reseal/repair window/door trim to reduce water/air intrusion.",
                450, ("window", "door", "seal", "frame", "caulk")),
    CatalogItem("exterior.paint_prep_spot", "paint",
                "Prep and spot-paint affected exterior areas to match existing finish.",
                400, ("paint", "peel", "peeling", "fade", "discolor")),
    CatalogItem("general.assessment_tm", "general",
                "On-site assessment and minor repairs (time & materials).",
                300, ()),   # fallback — no keywords, always scores 0
]


def match(title: str, notes: str) -> tuple[CatalogItem, str]:
    text = f"{title} {notes}".lower()
    best_item = CATALOG[-1]  # fallback
    best_score = 0
    best_hits: list[str] = []

    for item in CATALOG[:-1]:  # skip fallback in scoring loop
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
