"""Knowledge store — memory layer 4 (long documents: PDFs, papers, notes).

A per-user substrate of chunked + embedded documents over pgvector, isolated
by RLS. Coherence-aligned: ingestion feeds both this raw substrate (for
recall via `search_knowledge`) and the coherence engine (entity extraction),
so the graph remains the refinable source of truth.
"""
