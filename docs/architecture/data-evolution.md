# Data evolution — change_log + evidence graph

This doc covers how data CHANGES over time without losing history, and how
multi-source linking (Python used at job A, project B, course C) is modeled.

## `universe_change_log` (append-only)

Schema:

```sql
universe_change_log (
  id UUID PK,
  user_id UUID NOT NULL,
  entity_type TEXT NOT NULL,         -- 'skill' | 'experience' | …
  entity_id UUID NOT NULL,
  change_type TEXT NOT NULL,         -- 'create' | 'update' | 'delete' | 'merge'
  field TEXT,                         -- null for create/delete
  old_value JSONB,                    -- null for create
  new_value JSONB,                    -- null for delete
  reason TEXT,                        -- e.g. "upsert: merged via rules"
  source TEXT NOT NULL,               -- agent_chat | manual | curator | …
  agent_run_id TEXT,                  -- Agno run id (debug)
  changed_at TIMESTAMPTZ DEFAULT now()
)
INDEX (user_id, entity_type, entity_id, changed_at DESC)
INDEX (user_id, changed_at DESC)
RLS ON
```

The table is **append-only** at the application layer. Inserts come from
`SqlAlchemyChangeLogRepository.record(...)`. No UPDATE/DELETE paths.

### Querying

```python
repo = SqlAlchemyChangeLogRepository(session)

# Full timeline of one entity
await repo.list_for_entity(user_id=..., entity_type='skill', entity_id=..., limit=20)

# Last week, all entities
await repo.list_for_user(user_id=..., since=datetime.utcnow() - timedelta(days=7))
```

REST: `GET /api/v1/coherence/changes?limit=50&entity_type=skill&entity_id=...`

### What ends up in the log

- `change_type='create'`: first time an entity exists.
- `change_type='update'`: ONE ROW PER FIELD CHANGED in a merge.
- `change_type='delete'`: hard delete (rare; we prefer `mark_stale`).
- `change_type='merge'`: reserved for explicit consolidations by the curator
  (Sprint 4 doesn't write any yet; the upsert path uses `update`).

## Evidence graph

`evidences` table (created in migration 0003, activated in Sprint 4):

```sql
evidences (
  id UUID PK,
  user_id UUID,
  skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
  evidence_entity_type TEXT,        -- 'experience' | 'project' | 'course' | 'note' | …
  evidence_entity_id UUID,
  weight FLOAT DEFAULT 1.0,
  notes TEXT,
  created_at TIMESTAMPTZ
)
UNIQUE (skill_id, evidence_entity_type, evidence_entity_id)
INDEX (user_id, skill_id)
INDEX (user_id, evidence_entity_type, evidence_entity_id)  -- 0008
```

A skill can be linked to N entities; the reverse index lets us ask "what
skills does this project demonstrate?".

### Auto-linking

`SqlAlchemyEvidenceLinker.link(...)` is idempotent and is called by
`UpsertUniverseEntity._create` / `._merge` whenever a skill upsert payload
contains any `derived_from_<entity>_id` or `mentioned_in_note_id` field.
The agent passes these on `upsert_skill` tool calls so the graph forms
automatically as the user mentions things.

### Manual links

`/agents/tools/coherence_tools.py:link_evidence(skill_id, target_type, target_id)`
exists for the rare case the agent needs to link explicitly.

## Trajectory examples

### "When did I get expert at Python?"

```sql
SELECT changed_at, old_value, new_value
FROM universe_change_log
WHERE user_id = $1 AND entity_type='skill' AND field='level' AND new_value::text='"expert"'
ORDER BY changed_at ASC
LIMIT 1;
```

### "What have I been learning lately?"

```sql
SELECT entity_type, entity_id, COUNT(*) AS changes
FROM universe_change_log
WHERE user_id = $1
  AND changed_at > now() - INTERVAL '90 days'
  AND entity_type IN ('skill', 'interest', 'course')
GROUP BY entity_type, entity_id
ORDER BY changes DESC
LIMIT 10;
```

### "Python evidence stack"

```sql
SELECT e.evidence_entity_type, e.evidence_entity_id, e.weight, e.created_at
FROM evidences e
JOIN skills s ON s.id = e.skill_id
WHERE s.user_id = $1 AND lower(s.name) = 'python'
ORDER BY e.created_at DESC;
```

## Confidence decay

Curator decays `confidence` on entries unreviewed for 365+ days:
`confidence = GREATEST(confidence * 0.9, 0.3)`. The change goes into
`change_log` with `reason='curator: decay'`. Users see this in the
"Trayectoria" tab and the agent can flag stale entries proactively.

## Retention

The plan documents partitioning by month (`pg_partman`) or archival after
2 years. Not implemented in Sprint 4 — the table grows linearly with user
activity and stays bounded for the foreseeable usage.
