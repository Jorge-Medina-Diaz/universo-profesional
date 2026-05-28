"""Simple ESCO sample seeder for ontology_search table.

Usage:
    python -m scripts.seed_esco_simple
"""
from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.db import get_session_factory

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "esco_sample"


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = SAMPLE_DIR / filename
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        # Check if already seeded
        result = await session.execute(text("SELECT count(*) FROM ontology_search"))
        count = result.scalar()
        if count and count > 0:
            print(f"ontology_search already has {count} rows, skipping.")
            return

        occupations_en = _read_csv("occupations_en.csv")
        occupations_es = _read_csv("occupations_es.csv")
        skills_en = _read_csv("skills_en.csv")
        skills_es = _read_csv("skills_es.csv")

        # Build lookup dicts for ES translations
        occ_es = {r["conceptUri"]: r for r in occupations_es}
        skill_es = {r["conceptUri"]: r for r in skills_es}

        rows = []

        for r in occupations_en:
            uri = r["conceptUri"]
            es = occ_es.get(uri, {})
            alt_en = r.get("altLabels", "") or ""
            alt_es = es.get("altLabels", "") or ""
            rows.append({
                "uri": uri,
                "label": "Occupation",
                "pref_label_en": r.get("preferredLabel", ""),
                "pref_label_es": es.get("preferredLabel", ""),
                "alt_labels_en": alt_en.split("\n") if alt_en else [],
                "alt_labels_es": alt_es.split("\n") if alt_es else [],
                "description_en": r.get("description", ""),
                "description_es": es.get("description", ""),
            })

        for r in skills_en:
            uri = r["conceptUri"]
            es = skill_es.get(uri, {})
            alt_en = r.get("altLabels", "") or ""
            alt_es = es.get("altLabels", "") or ""
            rows.append({
                "uri": uri,
                "label": "Skill",
                "pref_label_en": r.get("preferredLabel", ""),
                "pref_label_es": es.get("preferredLabel", ""),
                "alt_labels_en": alt_en.split("\n") if alt_en else [],
                "alt_labels_es": alt_es.split("\n") if alt_es else [],
                "description_en": r.get("description", ""),
                "description_es": es.get("description", ""),
            })

        stmt = text("""
            INSERT INTO ontology_search
                (uri, label, pref_label_en, pref_label_es,
                 alt_labels_en, alt_labels_es, description_en, description_es)
            VALUES
                (:uri, :label, :pref_label_en, :pref_label_es,
                 :alt_labels_en, :alt_labels_es, :description_en, :description_es)
            ON CONFLICT (uri) DO NOTHING
        """)

        for row in rows:
            await session.execute(stmt, row)

        await session.commit()
        print(f"Seeded {len(rows)} rows into ontology_search.")


if __name__ == "__main__":
    asyncio.run(main())
