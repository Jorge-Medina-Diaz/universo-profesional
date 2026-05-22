"""Universe graph layer — Apache AGE backbone + ESCO ontology.

Sprint M introduces a hypergraph view of each user's universe. Personal
entities (skill, project, experience, …) become vertices in the
`universe_personal` AGE graph; relations that were previously implicit
(`evidences` table, `linked_skill_ids`, `related_project_id`, …) become
typed edges. A shared `universe_ontology` graph holds the ESCO backbone
(Occupations + Skills + ISCO groups) that personal nodes link to via
`:LINKS_TO_ESCO`.

Module structure (Clean Architecture):
    domain/         schema constants, node/edge dataclasses, registry
    application/    UniverseGraphService, ESCO linker, retrieval, episodes
    infrastructure/ age_client, ontology_loader, repositories
    interfaces/     FastAPI graph_router

See `docs/architecture/graph-rag.md` (written in Sprint R) for the full
schema and example Cypher queries.
"""
