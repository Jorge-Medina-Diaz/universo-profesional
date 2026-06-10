"""GitHub sync use case: fetch + map → universe entities.

P3.C: every write goes through the COHERENCE ENGINE (UpsertUniverseEntity)
instead of raw repositories — so GitHub imports finally get ESCO linking,
edge materialization, embeddings, change_log rows and snapshot invalidation,
exactly like chat captures. GitHub-specific identity rules are kept as
PRE-CHECKS (URL dedup for repos, level-upgrade-only for languages) and pin
the engine via entity_id/op_hint; ambiguous merges become `suggested` rows,
which surface in the P3.E review queue instead of silently writing.
"""
from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import structlog

from src.integrations.application.ports import (
    ExternalAccountRepository,
    OperationCancelledError,
    SyncRunsRepository,
)
from src.integrations.domain.external_account import IntegrationSynced
from src.integrations.application.ports.github import GithubClient
from src.shared.security import utc_now
from src.shared.uow import UnitOfWork
from src.universe.application.ports import (
    ExperienceRepository,
    InterestRepository,
    ProjectRepository,
    SkillRepository,
)

logger = structlog.get_logger(__name__)


# How big a language slice needs to be to count as a real skill
LANGUAGE_BYTE_FLOOR = 50_000
# Recency weight: pushes a repo from a year ago to ~0.5
RECENCY_HALF_LIFE_DAYS = 365.0


class SyncGithub:
    def __init__(
        self,
        accounts: ExternalAccountRepository,
        runs: SyncRunsRepository,
        projects: ProjectRepository,
        skills: SkillRepository,
        interests: InterestRepository,
        experiences: ExperienceRepository,
        session: Any = None,
    ) -> None:
        self._accounts = accounts
        self._runs = runs
        self._projects = projects
        self._skills = skills
        self._interests = interests
        self._experiences = experiences
        # AsyncSession for the coherence engine; required for writes (all
        # call sites pass it — typed Any to keep this layer ORM-agnostic).
        self._session = session

    def _upserter(self):  # type: ignore[no-untyped-def]
        from src.coherence.application.upsert_use_cases import UpsertUniverseEntity
        from src.coherence.infrastructure.change_log_repo import (
            SqlAlchemyChangeLogRepository,
        )
        from src.coherence.infrastructure.semantic_matcher import (
            PgVectorSemanticMatcher,
        )

        if self._session is None:
            raise RuntimeError("SyncGithub requires a session for coherent writes")
        return UpsertUniverseEntity(
            self._session,
            change_log=SqlAlchemyChangeLogRepository(self._session),
            semantic_matcher=PgVectorSemanticMatcher(self._session),
        )

    async def execute(self, *, user_id: str, uow: UnitOfWork) -> dict[str, Any]:
        uid = UUID(user_id)
        account = await self._accounts.get(uid, "github")
        if account is None or not account.access_token:
            raise RuntimeError("github account not connected")

        run_id = await self._runs.start(uid, "github")
        items_created = 0
        items_updated = 0
        items_suggested = 0
        errors: list[str] = []
        upserter = self._upserter()

        async def _coherent(
            entity_type: str,
            payload: dict[str, Any],
            *,
            entity_id: Any = None,
            op_hint: str | None = None,
        ) -> str:
            outcome = await upserter.execute(
                entity_type=entity_type,
                user_id=user_id,
                payload=payload,
                uow=uow,
                source="github",
                op_hint=op_hint,
                entity_id=str(entity_id) if entity_id else None,
            )
            return outcome.status.value

        async def _bail_if_cancelled(stage: str) -> None:
            if await self._runs.is_cancelled(run_id):
                raise OperationCancelledError(f"cancelled at {stage}")

        try:
            gh = GithubClient(account.access_token)
            me = await gh.get_authenticated_user()
            login = me["login"]

            repos = await gh.list_repos()
            await _bail_if_cancelled("after_list_repos")
            orgs = await gh.list_orgs()
            await _bail_if_cancelled("after_list_orgs")
            try:
                graphql_data = await gh.pinned_and_contributions(login)
            except Exception as exc:
                graphql_data = {}
                errors.append(f"graphql_failed: {exc}")

            # --- Projects from top repos ---
            scored = []
            now = utc_now()
            for r in repos:
                if r.get("fork") or r.get("archived"):
                    continue
                stars = r.get("stargazers_count", 0)
                pushed = _parse_iso(r.get("pushed_at"))
                recency = _recency_score(pushed, now)
                score = stars * 3 + math.log(max(1, stars)) * 2 + recency
                scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            top_repos = [r for _, r in scored[:10]]

            # Force-include pinned even if they didn't rank
            pinned_nodes = (
                ((graphql_data.get("user") or {}).get("pinnedItems") or {}).get("nodes") or []
            )
            pinned_names = {p["name"] for p in pinned_nodes if p}
            for r in repos:
                if r["name"] in pinned_names and r not in top_repos:
                    top_repos.append(r)

            # --- Aggregated language bytes across all repos ---
            language_bytes: dict[str, int] = {}
            for idx, r in enumerate(top_repos):
                # Cooperative cancel: this is the most expensive loop (N API
                # calls), so we check before each one rather than only once.
                if idx % 3 == 0:
                    await _bail_if_cancelled(f"during_langs[{idx}]")
                try:
                    langs = await gh.get_repo_languages(r["owner"]["login"], r["name"])
                    for k, v in langs.items():
                        language_bytes[k] = language_bytes.get(k, 0) + int(v)
                except Exception as exc:
                    errors.append(f"langs_{r['name']}: {exc}")

            await _bail_if_cancelled("before_projects_upsert")
            for r in top_repos:
                description = r.get("description") or ""
                # Optional README enrichment (skip if too big)
                if not description and r.get("size", 0) < 5000:
                    try:
                        readme = await gh.get_repo_readme(r["owner"]["login"], r["name"])
                        if readme:
                            description = _first_paragraph(readme)
                    except Exception:
                        pass

                existing = None
                # Dedup by URL
                for p in await self._projects.list(uid):
                    if p.url == r["html_url"]:
                        existing = p
                        break

                payload = {
                    "name": r["name"],
                    "description": description or None,
                    "url": r["html_url"],
                    "tech_stack": list(r.get("topics") or []),
                    "highlights": [],
                    "project_type": "oss" if r.get("license") else "side",
                    "role": "creator",
                    "status": "active" if not r.get("archived") else "archived",
                    "start_date": _parse_iso_date(r.get("created_at")),
                    "end_date": _parse_iso_date(r.get("pushed_at")) if r.get("archived") else None,
                    "is_current": not r.get("archived"),
                }
                payload["source_metadata"] = {
                    "repo": f"{r['owner']['login']}/{r['name']}",
                    "fetched_at": now.isoformat(),
                    "stars": r.get("stargazers_count", 0),
                }
                try:
                    status = await _coherent(
                        "project",
                        {k: v for k, v in payload.items() if v not in (None, "", [])},
                        entity_id=existing.id if existing else None,
                        op_hint="UPDATE" if existing else None,
                    )
                except Exception as exc:
                    errors.append(f"project_{r['name']}: {exc}")
                    continue
                if status == "created":
                    items_created += 1
                elif status == "suggested":
                    items_suggested += 1
                else:
                    items_updated += 1

            await _bail_if_cancelled("before_skills_upsert")
            # --- Skills from languages aggregated ---
            existing_skills_by_name = {
                s.name.lower(): s for s in await self._skills.list(uid)
            }
            for lang, byte_count in language_bytes.items():
                if byte_count < LANGUAGE_BYTE_FLOOR:
                    continue
                level = _level_from_bytes(byte_count)
                key = lang.lower()
                existing_skill = existing_skills_by_name.get(key)
                if existing_skill is not None and _level_rank(level) <= _level_rank(
                    existing_skill.level or ""
                ):
                    continue  # never downgrade a level the user already has
                try:
                    status = await _coherent(
                        "skill",
                        {
                            "name": lang,
                            "category": "hard",
                            "level": level,
                            "source_metadata": {
                                "bytes": byte_count,
                                "fetched_at": now.isoformat(),
                            },
                        },
                        entity_id=existing_skill.id if existing_skill else None,
                        op_hint="UPDATE" if existing_skill else None,
                    )
                except Exception as exc:
                    errors.append(f"skill_{lang}: {exc}")
                    continue
                if status == "created":
                    items_created += 1
                elif status == "suggested":
                    items_suggested += 1
                else:
                    items_updated += 1

            # --- Interests from topics ---
            topic_set: set[str] = set()
            for r in top_repos:
                for t in r.get("topics") or []:
                    topic_set.add(t)
            existing_interests = {i.name.lower() for i in await self._interests.list(uid)}
            for topic in list(topic_set)[:15]:
                if topic.lower() in existing_interests:
                    continue
                try:
                    status = await _coherent("interest", {"name": topic})
                except Exception as exc:
                    errors.append(f"interest_{topic}: {exc}")
                    continue
                if status == "created":
                    items_created += 1
                elif status == "suggested":
                    items_suggested += 1
                else:
                    items_updated += 1

            await _bail_if_cancelled("before_experiences_upsert")
            # --- Experiences from orgs (member of) ---
            existing_exp_keys = {
                (e.organization.lower(), e.role.lower()) for e in await self._experiences.list(uid)
            }
            for org in orgs:
                login_org = org.get("login")
                if not login_org:
                    continue
                key = (login_org.lower(), "contributor")
                if key in existing_exp_keys:
                    continue
                exp_payload: dict[str, Any] = {
                    "organization": login_org,
                    "role": "Contributor",
                    "employment_type": "contractor",
                    "modality": "remote",
                    "is_current": True,
                    "source_metadata": {
                        "org_url": org.get("url"),
                        "fetched_at": now.isoformat(),
                    },
                }
                if org.get("description"):
                    exp_payload["description"] = org["description"]
                try:
                    status = await _coherent("experience", exp_payload)
                except Exception as exc:
                    errors.append(f"experience_{login_org}: {exc}")
                    continue
                if status == "created":
                    items_created += 1
                elif status == "suggested":
                    items_suggested += 1
                else:
                    items_updated += 1

            await self._accounts.touch_sync(uid, "github", ok=True, error=None, when=now)
            await self._runs.finish(
                run_id,
                ok=True,
                items_created=items_created,
                items_updated=items_updated,
                error=None,
                summary={
                    "items_suggested": items_suggested,
                    "repos_scanned": len(repos),
                    "top_repos": [r["full_name"] for r in top_repos],
                    "languages": language_bytes,
                    "errors": errors,
                    "contributions": (graphql_data.get("user") or {}).get("contributionsCollection"),
                },
            )
            uow.add_event(
                IntegrationSynced(
                    user_id=uid,
                    provider="github",
                    items_created=items_created,
                    items_updated=items_updated,
                )
            )
            return {
                "ok": True,
                "items_created": items_created,
                "items_updated": items_updated,
            }
        except OperationCancelledError as exc:
            # Soft-cancel requested by the user. Mark the run as cancelled
            # (not a real failure) and preserve whatever we managed to upsert
            # before the checkpoint kicked in.
            logger.info(
                "github_sync_cancelled",
                items_created=items_created,
                items_updated=items_updated,
                stage=str(exc),
            )
            await self._accounts.touch_sync(
                uid, "github", ok=False, error="cancelled", when=utc_now()
            )
            await self._runs.finish(
                run_id,
                ok=False,
                items_created=items_created,
                items_updated=items_updated,
                error="cancelled",
                summary={"errors": errors, "cancelled_stage": str(exc)},
            )
            return {
                "ok": False,
                "error": "cancelled",
                "items_created": items_created,
                "items_updated": items_updated,
            }
        except Exception as exc:
            logger.exception("github_sync_failed", error=str(exc))
            await self._accounts.touch_sync(
                uid, "github", ok=False, error=str(exc), when=utc_now()
            )
            await self._runs.finish(
                run_id,
                ok=False,
                items_created=items_created,
                items_updated=items_updated,
                error=str(exc),
                summary={"errors": errors},
            )
            return {"ok": False, "error": str(exc)}


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_iso_date(s: str | None) -> date | None:
    dt = _parse_iso(s)
    return dt.date() if dt else None


def _recency_score(pushed: datetime | None, now: datetime) -> float:
    if pushed is None:
        return 0.0
    if pushed.tzinfo is None:
        pushed = pushed.replace(tzinfo=UTC)
    age_days = (now - pushed).total_seconds() / 86400.0
    return 10.0 * math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)


def _level_from_bytes(byte_count: int) -> str:
    if byte_count >= 1_000_000:
        return "expert"
    if byte_count >= 250_000:
        return "high"
    if byte_count >= 50_000:
        return "intermediate"
    return "basic"


_RANK = {"basic": 1, "intermediate": 2, "high": 3, "expert": 4, "": 0, None: 0}


def _level_rank(lvl: str | None) -> int:
    return _RANK.get(lvl or "", 0)


def _first_paragraph(text: str) -> str:
    # Strip headers, badges, blank lines; return up to 280 chars
    import re

    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)  # badges
    cleaned = re.sub(r"\[!\[[^\]]*\]\([^)]+\)\]\([^)]+\)", "", cleaned)
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
    if not paragraphs:
        return ""
    p = paragraphs[0]
    return p[:280] + ("…" if len(p) > 280 else "")
