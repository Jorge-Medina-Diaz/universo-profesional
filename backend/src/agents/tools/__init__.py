"""Tools wired to specialists.

Two flavours:

* `ui_widgets` — `@tool(external_execution=True)` declarations whose argument
  schema is the AG-UI payload the frontend renders as a HITL card. Their
  Python body is intentionally empty — execution happens in the React layer.

* read/query tools (`universe_reads`, `discovery_tools`, `graph_query_tools`,
  …) — async functions that run on a fresh DB session scoped to the current
  `run_context.user_id`. Persistence is never a tool: it happens when the user
  confirms the card, via the coherence-engine upsert use cases.
"""
