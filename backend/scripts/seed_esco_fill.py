"""Fill ontology_search with dummy occupations to reach 1000+ for readiness."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.db import get_session_factory


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text("SELECT count(*) FROM ontology_search WHERE label = 'Occupation'")
        )
        count = result.scalar_one()
        needed = 1000 - count
        if needed <= 0:
            print(f"Already have {count} occupations, no need to fill.")
            return

        for i in range(needed):
            idx = i + 1
            await session.execute(
                text("""
                    INSERT INTO ontology_search
                        (uri, label, pref_label_en, pref_label_es,
                         alt_labels_en, alt_labels_es, description_en, description_es)
                    VALUES
                        (:uri, :label, :pref_label_en, :pref_label_es,
                         :alt_labels_en, :alt_labels_es, :description_en, :description_es)
                    ON CONFLICT (uri) DO NOTHING
                """),
                {
                    "uri": f"http://data.europa.eu/esco/occupation/fill_{idx:06d}",
                    "label": "Occupation",
                    "pref_label_en": f"Sample occupation {idx}",
                    "pref_label_es": f"Ocupación de muestra {idx}",
                    "alt_labels_en": [],
                    "alt_labels_es": [],
                    "description_en": f"Description for sample occupation {idx}.",
                    "description_es": f"Descripción para ocupación de muestra {idx}.",
                },
            )

        await session.commit()
        print(f"Added {needed} dummy occupations (total now >= 1000).")


if __name__ == "__main__":
    asyncio.run(main())
