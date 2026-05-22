"""ESCO ontology loader — CSV → universe_ontology AGE graph + embeddings.

ESCO ships several distributions; the CSV bundle is the smallest and the
easiest to keep idempotent. Download from
https://esco.ec.europa.eu/en/use-esco/download and extract to a folder
containing (ES + EN versions for the labels we keep):

    occupations_es.csv
    occupations_en.csv
    skills_es.csv
    skills_en.csv
    ISCOGroups_es.csv
    ISCOGroups_en.csv
    occupationSkillRelations.csv     (language-agnostic)
    broaderRelationsOccPillar.csv    (SKOS-style broader, occupations)
    broaderRelationsSkillPillar.csv  (SKOS-style broader, skills)

Idempotency: we record the ESCO release version in `graph_ingest_meta`
and skip ingest if it matches. Pass `--force` on the CLI to override.
"""
from __future__ import annotations

import asyncio
import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema
from src.graph.infrastructure.age_client import cypher, ensure_age_loaded
from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Row dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _OccupationRow:
    uri: str
    isco_code: str
    pref_label_es: str | None
    pref_label_en: str | None
    alt_labels_es: list[str]
    alt_labels_en: list[str]
    description_es: str | None
    description_en: str | None


@dataclass(slots=True)
class _SkillRow:
    uri: str
    skill_type: str | None
    pref_label_es: str | None
    pref_label_en: str | None
    alt_labels_es: list[str]
    alt_labels_en: list[str]
    description_es: str | None
    description_en: str | None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _split_alt_labels(raw: str | None) -> list[str]:
    """ESCO alt labels are newline-separated within a single CSV cell."""
    if not raw:
        return []
    return [s.strip() for s in raw.replace("\r", "").split("\n") if s.strip()]


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        yield from reader


# ---------------------------------------------------------------------------
# Embedding text builders
# ---------------------------------------------------------------------------


def _embedding_text(
    pref_es: str | None,
    pref_en: str | None,
    alt_es: list[str],
    alt_en: list[str],
    desc_es: str | None,
    desc_en: str | None,
) -> str:
    """One multilingual embedding per concept.

    OpenAI text-embedding-3-small is multilingual enough that a single
    vector built from both labels + descriptions retrieves well in either
    language. This halves the cost vs storing two vectors per concept.
    """
    parts: list[str] = []
    if pref_es:
        parts.append(pref_es)
    if pref_en and pref_en != pref_es:
        parts.append(pref_en)
    alt_blob = ", ".join(alt_es[:6] + alt_en[:6])
    if alt_blob:
        parts.append(f"alt: {alt_blob}")
    if desc_es:
        parts.append(desc_es[:600])
    elif desc_en:
        parts.append(desc_en[:600])
    return " — ".join(parts)


# ---------------------------------------------------------------------------
# Loader entry point
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class IngestStats:
    occupations: int = 0
    skills: int = 0
    isco_groups: int = 0
    edges_occ_to_isco: int = 0
    edges_skill_to_occ_essential: int = 0
    edges_skill_to_occ_optional: int = 0
    edges_skos_broader_occ: int = 0
    edges_skos_broader_skill: int = 0
    skipped: bool = False


async def ingest_esco(
    session: AsyncSession,
    esco_dir: Path,
    *,
    force: bool = False,
    release_tag: str | None = None,
    embed_batch_size: int = 64,
    embed_concurrency: int = 4,
    progress: bool = True,
) -> IngestStats:
    """Load the ESCO CSV bundle into `universe_ontology`.

    Args:
        session: an AsyncSession bound to the cvs database.
        esco_dir: directory containing the ESCO CSV files listed above.
        force: re-ingest even if the release tag matches the last run.
        release_tag: explicit version tag (e.g. "v1.2.0"). If omitted,
            we hash the contents of the input directory.
        embed_batch_size: number of texts per OpenAI batch call.
        embed_concurrency: parallel embed batches.
        progress: log progress every 500 nodes.
    """
    await ensure_age_loaded(session)

    if release_tag is None:
        release_tag = await _compute_release_hash(esco_dir)

    if not force:
        prior = await session.execute(
            text("SELECT value FROM graph_ingest_meta WHERE name = :n"),
            {"n": "esco_release_version"},
        )
        prior_value = prior.scalar_one_or_none()
        if prior_value == release_tag:
            logger.info("esco_ingest_skipped", release_tag=release_tag)
            return IngestStats(skipped=True)

    stats = IngestStats()
    embeddings = get_embeddings_service()

    # ------------------------------------------------------------------
    # ISCO groups
    # ------------------------------------------------------------------
    isco_path = esco_dir / "ISCOGroups_es.csv"
    if isco_path.exists():
        isco_en = {
            row["conceptUri"]: row.get("preferredLabel", "")
            for row in _read_csv(esco_dir / "ISCOGroups_en.csv")
        }
        for row in _read_csv(isco_path):
            code = row.get("code", "").strip()
            if not code:
                continue
            await cypher(
                session,
                schema.GRAPH_ONTOLOGY,
                """
                MERGE (g:ISCOGroup {code: $code})
                SET g.label_es = $label_es,
                    g.label_en = $label_en
                """,
                params={
                    "code": code,
                    "label_es": row.get("preferredLabel", "") or None,
                    "label_en": isco_en.get(row["conceptUri"]) or None,
                },
            )
            stats.isco_groups += 1
            if progress and stats.isco_groups % 50 == 0:
                logger.info("esco_isco_progress", n=stats.isco_groups)

    # ------------------------------------------------------------------
    # Occupations
    # ------------------------------------------------------------------
    occ_rows = list(_iter_occupations(esco_dir))
    occ_embedding_texts = [
        _embedding_text(
            r.pref_label_es,
            r.pref_label_en,
            r.alt_labels_es,
            r.alt_labels_en,
            r.description_es,
            r.description_en,
        )
        for r in occ_rows
    ]
    occ_vectors = await _batch_embed(
        embeddings, occ_embedding_texts, embed_batch_size, embed_concurrency
    )
    for occ, emb in zip(occ_rows, occ_vectors, strict=True):
        await cypher(
            session,
            schema.GRAPH_ONTOLOGY,
            """
            MERGE (o:Occupation {uri: $uri})
            SET o.isco_code = $isco_code,
                o.pref_label_es = $pref_es,
                o.pref_label_en = $pref_en,
                o.alt_labels_es = $alt_es,
                o.alt_labels_en = $alt_en,
                o.description_es = $desc_es,
                o.description_en = $desc_en,
                o.embedding_dim = $dim
            """,
            params={
                "uri": occ.uri,
                "isco_code": occ.isco_code or None,
                "pref_es": occ.pref_label_es,
                "pref_en": occ.pref_label_en,
                "alt_es": occ.alt_labels_es,
                "alt_en": occ.alt_labels_en,
                "desc_es": occ.description_es,
                "desc_en": occ.description_en,
                "dim": len(emb) if emb is not None else 0,
            },
        )
        await _store_ontology_embedding(session, "Occupation", occ.uri, emb)
        if occ.isco_code:
            await cypher(
                session,
                schema.GRAPH_ONTOLOGY,
                """
                MATCH (o:Occupation {uri: $uri}), (g:ISCOGroup {code: $code})
                MERGE (o)-[:ISCO_GROUP_OF]->(g)
                """,
                params={"uri": occ.uri, "code": occ.isco_code},
            )
            stats.edges_occ_to_isco += 1
        stats.occupations += 1
        if progress and stats.occupations % 500 == 0:
            logger.info("esco_occupations_progress", n=stats.occupations)

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------
    skill_rows = list(_iter_skills(esco_dir))
    skill_embedding_texts = [
        _embedding_text(
            r.pref_label_es,
            r.pref_label_en,
            r.alt_labels_es,
            r.alt_labels_en,
            r.description_es,
            r.description_en,
        )
        for r in skill_rows
    ]
    skill_vectors = await _batch_embed(
        embeddings, skill_embedding_texts, embed_batch_size, embed_concurrency
    )
    for sk, emb in zip(skill_rows, skill_vectors, strict=True):
        await cypher(
            session,
            schema.GRAPH_ONTOLOGY,
            """
            MERGE (s:EscoSkill {uri: $uri})
            SET s.skill_type = $stype,
                s.pref_label_es = $pref_es,
                s.pref_label_en = $pref_en,
                s.alt_labels_es = $alt_es,
                s.alt_labels_en = $alt_en,
                s.description_es = $desc_es,
                s.description_en = $desc_en,
                s.embedding_dim = $dim
            """,
            params={
                "uri": sk.uri,
                "stype": sk.skill_type,
                "pref_es": sk.pref_label_es,
                "pref_en": sk.pref_label_en,
                "alt_es": sk.alt_labels_es,
                "alt_en": sk.alt_labels_en,
                "desc_es": sk.description_es,
                "desc_en": sk.description_en,
                "dim": len(emb) if emb is not None else 0,
            },
        )
        await _store_ontology_embedding(session, "EscoSkill", sk.uri, emb)
        stats.skills += 1
        if progress and stats.skills % 1000 == 0:
            logger.info("esco_skills_progress", n=stats.skills)

    # ------------------------------------------------------------------
    # Occupation × Skill relations (essential / optional)
    # ------------------------------------------------------------------
    rel_path = esco_dir / "occupationSkillRelations.csv"
    if rel_path.exists():
        for row in _read_csv(rel_path):
            occ_uri = row.get("occupationUri", "")
            skill_uri = row.get("skillUri", "")
            rel_type = row.get("relationType", "").lower()
            if not occ_uri or not skill_uri or rel_type not in {
                "essential",
                "optional",
            }:
                continue
            edge_kind = "ESSENTIAL_FOR" if rel_type == "essential" else "OPTIONAL_FOR"
            await cypher(
                session,
                schema.GRAPH_ONTOLOGY,
                f"""
                MATCH (s:EscoSkill {{uri: $skill_uri}}),
                      (o:Occupation {{uri: $occ_uri}})
                MERGE (s)-[:{edge_kind}]->(o)
                """,
                params={"skill_uri": skill_uri, "occ_uri": occ_uri},
            )
            if rel_type == "essential":
                stats.edges_skill_to_occ_essential += 1
            else:
                stats.edges_skill_to_occ_optional += 1

    # ------------------------------------------------------------------
    # SKOS broader within each pillar
    # ------------------------------------------------------------------
    for filename, edge_kind, counter_attr in (
        ("broaderRelationsOccPillar.csv", "SKOS_BROADER", "edges_skos_broader_occ"),
        (
            "broaderRelationsSkillPillar.csv",
            "SKOS_BROADER",
            "edges_skos_broader_skill",
        ),
    ):
        path = esco_dir / filename
        if not path.exists():
            continue
        for row in _read_csv(path):
            narrower = row.get("conceptUri") or row.get("narrowerUri")
            broader = row.get("broaderUri")
            if not narrower or not broader:
                continue
            label_n, label_b = ("Occupation", "Occupation") if "Occ" in filename else (
                "EscoSkill",
                "EscoSkill",
            )
            await cypher(
                session,
                schema.GRAPH_ONTOLOGY,
                f"""
                MATCH (n:{label_n} {{uri: $narrower}}),
                      (b:{label_b} {{uri: $broader}})
                MERGE (n)-[:{edge_kind}]->(b)
                """,
                params={"narrower": narrower, "broader": broader},
            )
            setattr(stats, counter_attr, getattr(stats, counter_attr) + 1)

    # ------------------------------------------------------------------
    # Record release version
    # ------------------------------------------------------------------
    await session.execute(
        text(
            """
            INSERT INTO graph_ingest_meta (name, value)
            VALUES ('esco_release_version', :v)
            ON CONFLICT (name) DO UPDATE
              SET value = EXCLUDED.value, updated_at = now()
            """
        ),
        {"v": release_tag},
    )

    logger.info("esco_ingest_completed", release_tag=release_tag, **stats.__dict__)
    return stats


# ---------------------------------------------------------------------------
# Iterators & embedding helpers
# ---------------------------------------------------------------------------


def _iter_occupations(esco_dir: Path) -> Iterator[_OccupationRow]:
    es_path = esco_dir / "occupations_es.csv"
    en_path = esco_dir / "occupations_en.csv"
    en_index = {row["conceptUri"]: row for row in _read_csv(en_path)}

    for row in _read_csv(es_path):
        uri = row["conceptUri"]
        en_row = en_index.get(uri, {})
        yield _OccupationRow(
            uri=uri,
            isco_code=row.get("iscoGroup", "").strip(),
            pref_label_es=row.get("preferredLabel") or None,
            pref_label_en=en_row.get("preferredLabel") or None,
            alt_labels_es=_split_alt_labels(row.get("altLabels")),
            alt_labels_en=_split_alt_labels(en_row.get("altLabels")),
            description_es=row.get("description") or None,
            description_en=en_row.get("description") or None,
        )


def _iter_skills(esco_dir: Path) -> Iterator[_SkillRow]:
    es_path = esco_dir / "skills_es.csv"
    en_path = esco_dir / "skills_en.csv"
    en_index = {row["conceptUri"]: row for row in _read_csv(en_path)}

    for row in _read_csv(es_path):
        uri = row["conceptUri"]
        en_row = en_index.get(uri, {})
        yield _SkillRow(
            uri=uri,
            skill_type=row.get("skillType") or None,
            pref_label_es=row.get("preferredLabel") or None,
            pref_label_en=en_row.get("preferredLabel") or None,
            alt_labels_es=_split_alt_labels(row.get("altLabels")),
            alt_labels_en=_split_alt_labels(en_row.get("altLabels")),
            description_es=row.get("description") or None,
            description_en=en_row.get("description") or None,
        )


async def _batch_embed(
    service: Any,
    texts: list[str],
    batch_size: int,
    concurrency: int,
) -> list[list[float] | None]:
    """Embed a flat list of texts in parallel batches.

    Falls back to None for any text that fails (so the ingest does not
    abort over a single malformed row).
    """
    sem = asyncio.Semaphore(concurrency)
    results: list[list[float] | None] = [None] * len(texts)

    async def _embed_chunk(start: int, chunk: list[str]) -> None:
        async with sem:
            try:
                vectors = await service.embed_batch(chunk)
            except Exception as exc:
                logger.warning("esco_embed_chunk_failed", start=start, error=str(exc))
                return
            for offset, vector in enumerate(vectors):
                results[start + offset] = vector

    tasks = [
        _embed_chunk(i, texts[i : i + batch_size])
        for i in range(0, len(texts), batch_size)
    ]
    if tasks:
        await asyncio.gather(*tasks)
    return results


async def _store_ontology_embedding(
    session: AsyncSession,
    label: str,
    uri: str,
    embedding: list[float] | None,
) -> None:
    """Persist the embedding into a side table for HNSW similarity.

    AGE's agtype properties don't index vectors efficiently, so we store
    the canonical embedding in a small relational table keyed by URI.
    Sprint N's ESCO linker queries this table directly via pgvector.
    """
    if embedding is None:
        return
    await session.execute(
        text(
            """
            INSERT INTO ontology_embeddings (label, uri, embedding)
            VALUES (:label, :uri, :emb::vector)
            ON CONFLICT (uri) DO UPDATE
              SET embedding = EXCLUDED.embedding,
                  label = EXCLUDED.label,
                  updated_at = now()
            """
        ),
        {"label": label, "uri": uri, "emb": embedding},
    )


# ---------------------------------------------------------------------------
# Release hashing — content-based version tag when no explicit tag provided.
# ---------------------------------------------------------------------------


async def _compute_release_hash(esco_dir: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    for name in sorted(p.name for p in esco_dir.glob("*.csv")):
        p = esco_dir / name
        h.update(name.encode())
        h.update(str(p.stat().st_size).encode())
        h.update(str(int(p.stat().st_mtime)).encode())
    return f"sha256:{h.hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# Standalone logging setup (when invoked as a script)
# ---------------------------------------------------------------------------


def configure_cli_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
