# Contributing

This is a personal portfolio project, not a product accepting roadmap
contributions. Bug reports and small fixes are welcome; please open an issue
before anything large so neither of us wastes an afternoon.

## Setup

```bash
cp .env.example .env          # defaults work fully offline
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

## Before you push

CI runs all of these, so run them locally first:

```bash
# backend
docker compose exec backend ruff check src tests
docker compose exec backend mypy src
docker compose exec backend lint-imports        # DDD layering contract
docker compose exec backend pytest -q

# frontend
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test -- --run
```

## The two rules that matter

1. **Layering is enforced, not suggested.** `import-linter` holds
   `interfaces → infrastructure → application → domain` across every bounded
   context. A cross-layer import fails the build; restructure rather than
   adding an exception.
2. **Errors must be visible.** No `except: pass`, no console-only failures. If
   something fails, the user sees it. A bare `try/except` around database work
   is especially dangerous here — see the savepoint note in
   `backend/src/universe/application/enrichment.py` for what it cost once.

By contributing you agree your work is licensed under AGPL-3.0-only.
