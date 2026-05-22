"""Tools wired to specialists.

Two flavours:

* `ui_widgets` — `@tool(external_execution=True)` declarations whose argument
  schema is the AG-UI payload the frontend renders as a HITL card. Their
  Python body is intentionally empty — execution happens in the React layer.

* `universe_writes` — async functions that call the universe CRUD use cases
  on a fresh DB session scoped to the current `run_context.user_id`.
"""
