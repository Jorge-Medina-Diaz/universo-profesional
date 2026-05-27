"""SQLAlchemy implementations of Universe ports.

Every entity has an analogous repository following the same pattern. We
intentionally keep mapping functions explicit rather than using a generic
mapper — the entities differ enough that magic mapping leaks more bugs
than the duplication costs.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.security import utc_now
from src.universe.application.ports import (
    CareerPreferencesRepository,
    LanguageRepository,
    SkillRepository,
    UniverseRepository,
)
from src.universe.domain.entities import (
    Achievement,
    ArchitectureDecision,
    AreaStrength,
    Artifact,
    CareerPreferences,
    Certification,
    Course,
    Education,
    Experience,
    Interest,
    Language,
    Project,
    Skill,
    SkillStack,
    UserRubricSignal,
)
from src.universe.domain.universe import Universe
from src.universe.infrastructure.orm import (
    AchievementOrm,
    ArchitectureDecisionOrm,
    AreaStrengthOrm,
    ArtifactOrm,
    CareerPreferencesOrm,
    CertificationOrm,
    CourseOrm,
    EducationOrm,
    ExperienceOrm,
    InterestOrm,
    LanguageOrm,
    ProjectOrm,
    SkillOrm,
    SkillStackOrm,
    UniverseOrm,
    UserRubricSignalOrm,
)

# --- Universe --------------------------------------------------------------


class SqlAlchemyUniverseRepository(UniverseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> Universe | None:
        row = await self._session.get(UniverseOrm, user_id)
        if row is None:
            return None
        return Universe(
            user_id=row.user_id,
            headline=row.headline,
            summary=row.summary,
            photo_url=row.photo_url,
            current_status=row.current_status,
            last_reviewed_at=row.last_reviewed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def save(self, universe: Universe) -> None:
        existing = await self._session.get(UniverseOrm, universe.user_id)
        if existing is None:
            self._session.add(
                UniverseOrm(
                    user_id=universe.user_id,
                    headline=universe.headline,
                    summary=universe.summary,
                    photo_url=universe.photo_url,
                    current_status=universe.current_status,
                    last_reviewed_at=universe.last_reviewed_at,
                    created_at=universe.created_at,
                    updated_at=universe.updated_at,
                )
            )
        else:
            existing.headline = universe.headline
            existing.summary = universe.summary
            existing.photo_url = universe.photo_url
            existing.current_status = universe.current_status
            existing.last_reviewed_at = universe.last_reviewed_at
            existing.updated_at = universe.updated_at
        await self._session.flush()


# --- Helper: a small declarative mapping table --------------------------------
# For repositories that share the exact same shape (insert/update/delete +
# update_embedding), we generate them in-place to avoid a wall of duplicate code.


def _entity_to_orm_kwargs(entity: Any, orm_cls: Any) -> dict[str, Any]:
    """Pick fields from the dataclass entity that exist on the ORM class."""
    orm_cols = {c.name for c in orm_cls.__table__.columns}
    out: dict[str, Any] = {}
    for f in entity.__dataclass_fields__:
        if f.startswith("_"):
            continue
        if f in orm_cols:
            out[f] = getattr(entity, f)
    return out


def _orm_to_entity(row: Any, entity_cls: Any) -> Any:
    """Map ORM row → entity dataclass. Fields not present on the entity are dropped."""
    fields = {f for f in entity_cls.__dataclass_fields__ if not f.startswith("_")}
    kwargs = {f: getattr(row, f) for f in fields if hasattr(row, f)}
    return entity_cls(**kwargs)


# --- Generic repo body ---


def _build_repo_methods(orm_cls: Any, entity_cls: Any) -> dict[str, Any]:
    """Return a dict of methods implementing the standard repo Protocol."""

    async def list_(self: Any, user_id: UUID) -> list[Any]:
        stmt = select(orm_cls).where(orm_cls.user_id == user_id).where(orm_cls.deleted_at.is_(None) if hasattr(orm_cls, "deleted_at") else True)  # type: ignore[arg-type]
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_entity(r, entity_cls) for r in rows]

    async def get_(self: Any, user_id: UUID, entity_id: UUID) -> Any | None:
        stmt = select(orm_cls).where(orm_cls.id == entity_id).where(orm_cls.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _orm_to_entity(row, entity_cls)

    async def add_(self: Any, entity: Any) -> None:
        self._session.add(orm_cls(**_entity_to_orm_kwargs(entity, orm_cls)))
        await self._session.flush()

    async def update_(self: Any, entity: Any) -> None:
        existing = await self._session.get(orm_cls, entity.id)
        if existing is None:
            return
        for k, v in _entity_to_orm_kwargs(entity, orm_cls).items():
            setattr(existing, k, v)
        existing.updated_at = utc_now()
        await self._session.flush()

    async def delete_(self: Any, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            delete(orm_cls)
            .where(orm_cls.id == entity_id)
            .where(orm_cls.user_id == user_id)
            .returning(orm_cls.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def update_embedding_(self: Any, entity_id: UUID, embedding: list[float]) -> None:
        stmt = (
            update(orm_cls)
            .where(orm_cls.id == entity_id)
            .values(embedding=embedding, updated_at=utc_now())
        )
        await self._session.execute(stmt)
        await self._session.flush()

    return {
        "list": list_,
        "get": get_,
        "add": add_,
        "update": update_,
        "delete": delete_,
        "update_embedding": update_embedding_,
    }


class _BaseRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


def _make_repo(name: str, orm_cls: Any, entity_cls: Any) -> type:
    methods = _build_repo_methods(orm_cls, entity_cls)
    return type(name, (_BaseRepo,), methods)


SqlAlchemyEducationRepository = _make_repo(
    "SqlAlchemyEducationRepository", EducationOrm, Education
)
SqlAlchemyExperienceRepository = _make_repo(
    "SqlAlchemyExperienceRepository", ExperienceOrm, Experience
)
SqlAlchemyProjectRepository = _make_repo("SqlAlchemyProjectRepository", ProjectOrm, Project)
SqlAlchemyCertificationRepository = _make_repo(
    "SqlAlchemyCertificationRepository", CertificationOrm, Certification
)
SqlAlchemyCourseRepository = _make_repo("SqlAlchemyCourseRepository", CourseOrm, Course)
SqlAlchemyAchievementRepository = _make_repo(
    "SqlAlchemyAchievementRepository", AchievementOrm, Achievement
)
SqlAlchemyInterestRepository = _make_repo("SqlAlchemyInterestRepository", InterestOrm, Interest)
SqlAlchemyArchitectureDecisionRepository = _make_repo(
    "SqlAlchemyArchitectureDecisionRepository",
    ArchitectureDecisionOrm,
    ArchitectureDecision,
)


class SqlAlchemyLanguageRepository(_BaseRepo, LanguageRepository):
    """Languages have a unique constraint on (user_id, code) — we handle that here."""

    async def list(self, user_id: UUID) -> list[Language]:
        stmt = select(LanguageOrm).where(LanguageOrm.user_id == user_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_entity(r, Language) for r in rows]

    async def get(self, user_id: UUID, entity_id: UUID) -> Language | None:
        stmt = select(LanguageOrm).where(LanguageOrm.id == entity_id).where(
            LanguageOrm.user_id == user_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _orm_to_entity(row, Language) if row else None

    async def add(self, entity: Language) -> None:
        self._session.add(LanguageOrm(**_entity_to_orm_kwargs(entity, LanguageOrm)))
        await self._session.flush()

    async def update(self, entity: Language) -> None:
        existing = await self._session.get(LanguageOrm, entity.id)
        if existing is None:
            return
        for k, v in _entity_to_orm_kwargs(entity, LanguageOrm).items():
            setattr(existing, k, v)
        existing.updated_at = utc_now()
        await self._session.flush()

    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            delete(LanguageOrm)
            .where(LanguageOrm.id == entity_id)
            .where(LanguageOrm.user_id == user_id)
            .returning(LanguageOrm.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None


class SqlAlchemySkillRepository(_BaseRepo, SkillRepository):
    async def list(self, user_id: UUID) -> list[Skill]:
        stmt = select(SkillOrm).where(SkillOrm.user_id == user_id).where(
            SkillOrm.deleted_at.is_(None)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_entity(r, Skill) for r in rows]

    async def get(self, user_id: UUID, entity_id: UUID) -> Skill | None:
        stmt = select(SkillOrm).where(SkillOrm.id == entity_id).where(
            SkillOrm.user_id == user_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _orm_to_entity(row, Skill) if row else None

    async def add(self, entity: Skill) -> None:
        self._session.add(SkillOrm(**_entity_to_orm_kwargs(entity, SkillOrm)))
        await self._session.flush()

    async def update(self, entity: Skill) -> None:
        existing = await self._session.get(SkillOrm, entity.id)
        if existing is None:
            return
        for k, v in _entity_to_orm_kwargs(entity, SkillOrm).items():
            setattr(existing, k, v)
        existing.updated_at = utc_now()
        await self._session.flush()

    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            delete(SkillOrm)
            .where(SkillOrm.id == entity_id)
            .where(SkillOrm.user_id == user_id)
            .returning(SkillOrm.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def update_embedding(self, entity_id: UUID, embedding: list[float]) -> None:
        stmt = update(SkillOrm).where(SkillOrm.id == entity_id).values(
            embedding=embedding, updated_at=utc_now()
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def find_by_name(self, user_id: UUID, name: str) -> Skill | None:
        stmt = (
            select(SkillOrm)
            .where(SkillOrm.user_id == user_id)
            .where(SkillOrm.name.ilike(name))
            .where(SkillOrm.deleted_at.is_(None))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _orm_to_entity(row, Skill) if row else None


class SqlAlchemyCareerPreferencesRepository(_BaseRepo, CareerPreferencesRepository):
    async def get(self, user_id: UUID) -> CareerPreferences | None:
        row = await self._session.get(CareerPreferencesOrm, user_id)
        if row is None:
            return None
        return CareerPreferences(
            user_id=row.user_id,
            status=row.status,
            salary_min=float(row.salary_min) if row.salary_min is not None else None,
            salary_max=float(row.salary_max) if row.salary_max is not None else None,
            salary_currency=row.salary_currency,
            contract_types=list(row.contract_types or []),
            remote_preference=row.remote_preference,
            open_to_relocate=row.open_to_relocate,
            working_areas=row.working_areas or [],
            perks_must_have=row.perks_must_have or [],
            perks_nice_to_have=row.perks_nice_to_have or [],
            preferred_competences=list(row.preferred_competences or []),
            discarded_competences=list(row.discarded_competences or []),
            preferred_roles=list(row.preferred_roles or []),
            discarded_roles=list(row.discarded_roles or []),
            motivations=row.motivations,
            updated_at=row.updated_at,
        )

    async def upsert(self, prefs: CareerPreferences) -> None:
        existing = await self._session.get(CareerPreferencesOrm, prefs.user_id)
        if existing is None:
            self._session.add(
                CareerPreferencesOrm(
                    user_id=prefs.user_id,
                    status=prefs.status,
                    salary_min=prefs.salary_min,
                    salary_max=prefs.salary_max,
                    salary_currency=prefs.salary_currency,
                    contract_types=prefs.contract_types,
                    remote_preference=prefs.remote_preference,
                    open_to_relocate=prefs.open_to_relocate,
                    working_areas=prefs.working_areas,
                    perks_must_have=prefs.perks_must_have,
                    perks_nice_to_have=prefs.perks_nice_to_have,
                    preferred_competences=prefs.preferred_competences,
                    discarded_competences=prefs.discarded_competences,
                    preferred_roles=prefs.preferred_roles,
                    discarded_roles=prefs.discarded_roles,
                    motivations=prefs.motivations,
                    updated_at=prefs.updated_at,
                )
            )
        else:
            existing.status = prefs.status
            existing.salary_min = prefs.salary_min
            existing.salary_max = prefs.salary_max
            existing.salary_currency = prefs.salary_currency
            existing.contract_types = prefs.contract_types
            existing.remote_preference = prefs.remote_preference
            existing.open_to_relocate = prefs.open_to_relocate
            existing.working_areas = prefs.working_areas
            existing.perks_must_have = prefs.perks_must_have
            existing.perks_nice_to_have = prefs.perks_nice_to_have
            existing.preferred_competences = prefs.preferred_competences
            existing.discarded_competences = prefs.discarded_competences
            existing.preferred_roles = prefs.preferred_roles
            existing.discarded_roles = prefs.discarded_roles
            existing.motivations = prefs.motivations
            existing.updated_at = prefs.updated_at
        await self._session.flush()


# --- AreaStrength ---------------------------------------------------------


class SqlAlchemyAreaStrengthRepository(_BaseRepo):
    async def list(self, user_id: UUID) -> list[AreaStrength]:
        stmt = select(AreaStrengthOrm).where(AreaStrengthOrm.user_id == user_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def upsert(self, strength: AreaStrength) -> None:
        stmt = (
            select(AreaStrengthOrm)
            .where(AreaStrengthOrm.user_id == strength.user_id)
            .where(AreaStrengthOrm.area == strength.area)
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            self._session.add(
                AreaStrengthOrm(
                    id=strength.id,
                    user_id=strength.user_id,
                    area=strength.area,
                    depth_years=strength.depth_years,
                    breadth_count=strength.breadth_count,
                    recency_months=strength.recency_months,
                    confidence=strength.confidence,
                    is_primary=strength.is_primary,
                    computed_at=strength.computed_at,
                )
            )
        else:
            existing.depth_years = strength.depth_years
            existing.breadth_count = strength.breadth_count
            existing.recency_months = strength.recency_months
            existing.confidence = strength.confidence
            existing.is_primary = strength.is_primary
            existing.computed_at = strength.computed_at
        await self._session.flush()

    async def delete_areas(self, user_id: UUID, areas: list[str]) -> int:
        if not areas:
            return 0
        stmt = (
            delete(AreaStrengthOrm)
            .where(AreaStrengthOrm.user_id == user_id)
            .where(AreaStrengthOrm.area.in_(areas))
            .returning(AreaStrengthOrm.id)
        )
        result = await self._session.execute(stmt)
        return len(result.all())

    @staticmethod
    def _to_entity(row: AreaStrengthOrm) -> AreaStrength:
        return AreaStrength(
            id=row.id,
            user_id=row.user_id,
            area=row.area,
            depth_years=float(row.depth_years),
            breadth_count=row.breadth_count,
            recency_months=row.recency_months,
            confidence=float(row.confidence),
            is_primary=row.is_primary,
            computed_at=row.computed_at,
        )


# --- Artifact -------------------------------------------------------------


class SqlAlchemyArtifactRepository(_BaseRepo):
    async def list(
        self, user_id: UUID, type: str | None = None
    ) -> list[Artifact]:
        stmt = (
            select(ArtifactOrm)
            .where(ArtifactOrm.user_id == user_id)
            .where(ArtifactOrm.deleted_at.is_(None))
        )
        if type:
            stmt = stmt.where(ArtifactOrm.type == type)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def get(self, user_id: UUID, entity_id: UUID) -> Artifact | None:
        stmt = (
            select(ArtifactOrm)
            .where(ArtifactOrm.id == entity_id)
            .where(ArtifactOrm.user_id == user_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def add(self, artifact: Artifact) -> None:
        self._session.add(
            ArtifactOrm(
                id=artifact.id,
                user_id=artifact.user_id,
                type=artifact.type,
                title=artifact.title,
                url=artifact.url,
                year=artifact.year,
                description=artifact.description,
                venue=artifact.venue,
                metrics=artifact.metrics,
                source=artifact.source,
                visibility=artifact.visibility,
                confidence=artifact.confidence,
                source_metadata=artifact.source_metadata,
                last_reviewed_at=artifact.last_reviewed_at,
                created_at=artifact.created_at,
                updated_at=artifact.updated_at,
                deleted_at=artifact.deleted_at,
            )
        )
        await self._session.flush()

    async def update(self, artifact: Artifact) -> None:
        existing = await self._session.get(ArtifactOrm, artifact.id)
        if existing is None:
            return
        existing.type = artifact.type
        existing.title = artifact.title
        existing.url = artifact.url
        existing.year = artifact.year
        existing.description = artifact.description
        existing.venue = artifact.venue
        existing.metrics = artifact.metrics
        existing.updated_at = utc_now()
        await self._session.flush()

    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            delete(ArtifactOrm)
            .where(ArtifactOrm.id == entity_id)
            .where(ArtifactOrm.user_id == user_id)
            .returning(ArtifactOrm.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    @staticmethod
    def _to_entity(row: ArtifactOrm) -> Artifact:
        return Artifact(
            id=row.id,
            user_id=row.user_id,
            type=row.type,
            title=row.title,
            url=row.url,
            year=row.year,
            description=row.description,
            venue=row.venue,
            metrics=row.metrics,
            source=row.source,
            visibility=row.visibility,
            confidence=float(row.confidence) if row.confidence is not None else None,
            source_metadata=row.source_metadata,
            last_reviewed_at=row.last_reviewed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )


# --- SkillStack -----------------------------------------------------------


class SqlAlchemySkillStackRepository(_BaseRepo):
    async def list(self, user_id: UUID) -> list[SkillStack]:
        stmt = (
            select(SkillStackOrm)
            .where(SkillStackOrm.user_id == user_id)
            .where(SkillStackOrm.deleted_at.is_(None))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def get(self, user_id: UUID, entity_id: UUID) -> SkillStack | None:
        stmt = (
            select(SkillStackOrm)
            .where(SkillStackOrm.id == entity_id)
            .where(SkillStackOrm.user_id == user_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_by_slug(self, user_id: UUID, slug: str) -> SkillStack | None:
        stmt = (
            select(SkillStackOrm)
            .where(SkillStackOrm.user_id == user_id)
            .where(SkillStackOrm.slug == slug)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def add(self, stack: SkillStack) -> None:
        self._session.add(
            SkillStackOrm(
                id=stack.id,
                user_id=stack.user_id,
                name=stack.name,
                slug=stack.slug,
                area=stack.area,
                skill_ids=stack.skill_ids,
                description=stack.description,
                created_at=stack.created_at,
                updated_at=stack.updated_at,
                deleted_at=stack.deleted_at,
            )
        )
        await self._session.flush()

    async def update(self, stack: SkillStack) -> None:
        existing = await self._session.get(SkillStackOrm, stack.id)
        if existing is None:
            return
        existing.name = stack.name
        existing.area = stack.area
        existing.skill_ids = stack.skill_ids
        existing.description = stack.description
        existing.updated_at = utc_now()
        await self._session.flush()

    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            delete(SkillStackOrm)
            .where(SkillStackOrm.id == entity_id)
            .where(SkillStackOrm.user_id == user_id)
            .returning(SkillStackOrm.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    @staticmethod
    def _to_entity(row: SkillStackOrm) -> SkillStack:
        return SkillStack(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            slug=row.slug,
            area=row.area,
            skill_ids=list(row.skill_ids or []),
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )


# --- UserRubricSignal (overlay personal sobre rúbricas globales) ---------


class SqlAlchemyUserRubricSignalRepository(_BaseRepo):
    async def list(
        self,
        user_id: UUID,
        *,
        sector: str | None = None,
        status: str | None = None,
    ) -> list[UserRubricSignal]:
        from src.rubrics.infrastructure.orm import RubricChunkOrm

        stmt = (
            select(UserRubricSignalOrm)
            .where(UserRubricSignalOrm.user_id == user_id)
            .where(UserRubricSignalOrm.deleted_at.is_(None))
        )
        if status:
            stmt = stmt.where(UserRubricSignalOrm.status == status)
        if sector:
            # join via rubric_chunks.sector (denormalized)
            stmt = stmt.join(
                RubricChunkOrm,
                RubricChunkOrm.id == UserRubricSignalOrm.rubric_chunk_id,
            ).where(RubricChunkOrm.sector == sector)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows]

    async def get_by_chunk(
        self, user_id: UUID, rubric_chunk_id: UUID
    ) -> UserRubricSignal | None:
        stmt = (
            select(UserRubricSignalOrm)
            .where(UserRubricSignalOrm.user_id == user_id)
            .where(UserRubricSignalOrm.rubric_chunk_id == rubric_chunk_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def upsert(self, signal: UserRubricSignal) -> tuple[UserRubricSignal, bool]:
        """Returns (entity, was_created)."""
        stmt = (
            select(UserRubricSignalOrm)
            .where(UserRubricSignalOrm.user_id == signal.user_id)
            .where(UserRubricSignalOrm.rubric_chunk_id == signal.rubric_chunk_id)
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            self._session.add(
                UserRubricSignalOrm(
                    id=signal.id,
                    user_id=signal.user_id,
                    rubric_chunk_id=signal.rubric_chunk_id,
                    section_kind=signal.section_kind,
                    status=signal.status,
                    confidence=signal.confidence,
                    evidence_entity_type=signal.evidence_entity_type,
                    evidence_entity_ids=signal.evidence_entity_ids,
                    notes=signal.notes,
                    source=signal.source,
                    last_reviewed_at=signal.last_reviewed_at,
                    created_at=signal.created_at,
                    updated_at=signal.updated_at,
                )
            )
            await self._session.flush()
            return (signal, True)
        # Update in-place
        existing.section_kind = signal.section_kind
        existing.status = signal.status
        existing.confidence = signal.confidence
        existing.evidence_entity_type = signal.evidence_entity_type
        existing.evidence_entity_ids = signal.evidence_entity_ids
        existing.notes = signal.notes
        existing.source = signal.source
        existing.updated_at = utc_now()
        await self._session.flush()
        signal.id = existing.id
        return (signal, False)

    async def mark_stale(self, user_id: UUID, entity_id: UUID) -> bool:
        stmt = (
            update(UserRubricSignalOrm)
            .where(UserRubricSignalOrm.id == entity_id)
            .where(UserRubricSignalOrm.user_id == user_id)
            .values(deleted_at=utc_now(), updated_at=utc_now())
            .returning(UserRubricSignalOrm.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def delete_for_chunks(
        self, user_id: UUID, rubric_chunk_ids: list[UUID]
    ) -> int:
        if not rubric_chunk_ids:
            return 0
        stmt = (
            delete(UserRubricSignalOrm)
            .where(UserRubricSignalOrm.user_id == user_id)
            .where(UserRubricSignalOrm.rubric_chunk_id.in_(rubric_chunk_ids))
            .returning(UserRubricSignalOrm.id)
        )
        result = await self._session.execute(stmt)
        return len(result.all())

    @staticmethod
    def _to_entity(row: UserRubricSignalOrm) -> UserRubricSignal:
        return UserRubricSignal(
            id=row.id,
            user_id=row.user_id,
            rubric_chunk_id=row.rubric_chunk_id,
            section_kind=row.section_kind,
            status=row.status,
            confidence=float(row.confidence),
            evidence_entity_type=row.evidence_entity_type,
            evidence_entity_ids=list(row.evidence_entity_ids or []),
            notes=row.notes,
            source=row.source,
            last_reviewed_at=row.last_reviewed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )


# --- Helpers para shape_service (lectura + write directa al universo) -------


async def update_universe_areas(
    session: AsyncSession,
    user_id: UUID,
    primary_area: str | None,
    secondary_areas: list[str],
) -> None:
    """Updates the cached primary/secondary areas on universes row."""
    existing = await session.get(UniverseOrm, user_id)
    if existing is None:
        return
    existing.primary_area = primary_area
    existing.secondary_areas = list(secondary_areas)
    existing.updated_at = utc_now()
    await session.flush()


# ---------------------------------------------------------------------------
# Wire module-level ports so application layer stays import-clean.
# ---------------------------------------------------------------------------

from src.universe.application.ports import repositories as _repo_port  # noqa: E402

_repo_port.SqlAlchemyEducationRepository = SqlAlchemyEducationRepository
_repo_port.SqlAlchemyExperienceRepository = SqlAlchemyExperienceRepository
_repo_port.SqlAlchemyProjectRepository = SqlAlchemyProjectRepository
_repo_port.SqlAlchemySkillRepository = SqlAlchemySkillRepository
_repo_port.SqlAlchemyCertificationRepository = SqlAlchemyCertificationRepository
_repo_port.SqlAlchemyCourseRepository = SqlAlchemyCourseRepository
_repo_port.SqlAlchemyLanguageRepository = SqlAlchemyLanguageRepository
_repo_port.SqlAlchemyAchievementRepository = SqlAlchemyAchievementRepository
_repo_port.SqlAlchemyInterestRepository = SqlAlchemyInterestRepository
_repo_port.SqlAlchemyArtifactRepository = SqlAlchemyArtifactRepository
_repo_port.SqlAlchemyArchitectureDecisionRepository = SqlAlchemyArchitectureDecisionRepository
_repo_port.SqlAlchemyUserRubricSignalRepository = SqlAlchemyUserRubricSignalRepository
_repo_port.SqlAlchemyAreaStrengthRepository = SqlAlchemyAreaStrengthRepository
_repo_port.update_universe_areas = update_universe_areas
