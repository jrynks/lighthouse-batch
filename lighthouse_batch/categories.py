"""Category aliases → Lighthouse category ids. Unknown aliases are rejected."""

from __future__ import annotations

LH_IDS = {
    "perf": "performance",
    "performance": "performance",
    "a11y": "accessibility",
    "accessibility": "accessibility",
    "bp": "best-practices",
    "best-practices": "best-practices",
    "best_practices": "best-practices",
    "bestpractices": "best-practices",
    "seo": "seo",
}

DEFAULT_CATEGORIES = ("performance", "accessibility", "best-practices", "seo")

# Lighthouse id → schema field
TO_SCHEMA = {
    "performance": "performance",
    "accessibility": "accessibility",
    "best-practices": "best_practices",
    "seo": "seo",
}

PSI_CATEGORY = {
    "performance": "PERFORMANCE",
    "accessibility": "ACCESSIBILITY",
    "best-practices": "BEST_PRACTICES",
    "seo": "SEO",
}


def parse_categories(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return list(DEFAULT_CATEGORIES)
    out: list[str] = []
    seen: set[str] = set()
    for part in str(raw).split(","):
        token = part.strip().lower()
        if not token:
            continue
        if token not in LH_IDS:
            raise ValueError(
                f"unknown category {part!r}; expected perf,a11y,bp,seo "
                "(or performance,accessibility,best-practices,seo)"
            )
        lid = LH_IDS[token]
        if lid not in seen:
            seen.add(lid)
            out.append(lid)
    if not out:
        return list(DEFAULT_CATEGORIES)
    return out
