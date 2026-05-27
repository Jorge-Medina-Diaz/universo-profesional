"""Unit tests for universe application crud helpers + mocked CRUD methods."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.shared.result import Success
from src.shared.uow import UnitOfWork
from src.universe.application.crud import (
    AchievementCrud,
    ArchitectureDecisionCrud,
    ArtifactCrud,
    CertificationCrud,
    CourseCrud,
    EducationCrud,
    ExperienceCrud,
    InterestCrud,
    LanguageCrud,
    ProjectCrud,
    SkillCrud,
    _coerce,
    _serialize,
)
from src.universe.domain.entities import Certification, Education, Experience, Project, Skill


class TestCoerce:
    def test_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        assert _coerce(dt) == "2024-01-01T12:00:00+00:00"

    def test_uuid(self):
        u = uuid4()
        assert _coerce(u) == str(u)

    def test_list(self):
        u = uuid4()
        assert _coerce([u]) == [str(u)]

    def test_dict(self):
        u = uuid4()
        assert _coerce({"a": u}) == {"a": str(u)}

    def test_primitive(self):
        assert _coerce(42) == 42


class TestSerialize:
    def test_drops_events(self):
        e = Education.create(user_id=uuid4(), institution="USE")
        d = _serialize(e)
        assert "_events" not in d
        assert d["institution"] == "USE"


class TestEducationCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = EducationCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(user_id=str(uuid4()), payload={"institution": "USE"}, uow=uow)
        assert result.is_success
        repo.add.assert_awaited_once()

    async def test_add_validation_error(self):
        repo = MagicMock()
        sched = MagicMock()
        crud = EducationCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        result = await crud.add(user_id=str(uuid4()), payload={"institution": ""}, uow=uow)
        assert result.is_failure

    async def test_get_found(self):
        repo = MagicMock()
        entity = Education.create(user_id=uuid4(), institution="USE")
        repo.get = AsyncMock(return_value=entity)
        crud = EducationCrud(repo, MagicMock())
        result = await crud.get(user_id=str(entity.user_id), entity_id=str(entity.id))
        assert result.is_success

    async def test_get_not_found(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=None)
        crud = EducationCrud(repo, MagicMock())
        result = await crud.get(user_id=str(uuid4()), entity_id=str(uuid4()))
        assert result.is_failure

    async def test_delete_success(self):
        repo = MagicMock()
        repo.delete = AsyncMock(return_value=True)
        crud = EducationCrud(repo, MagicMock())
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.delete(user_id=str(uuid4()), entity_id=str(uuid4()), uow=uow)
        assert result.is_success


class TestExperienceCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = ExperienceCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"organization": "Acme", "role": "Dev"}, uow=uow
        )
        assert result.is_success

    async def test_update_success(self):
        entity = Experience.create(user_id=uuid4(), organization="Acme", role="Dev")
        repo = MagicMock()
        repo.get = AsyncMock(return_value=entity)
        repo.update = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = ExperienceCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.update(
            user_id=str(entity.user_id), entity_id=str(entity.id), patch={"role": "Senior"}, uow=uow
        )
        assert result.is_success
        assert entity.role == "Senior"


class TestProjectCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = ProjectCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(user_id=str(uuid4()), payload={"name": "demo"}, uow=uow)
        assert result.is_success


class TestSkillCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        repo.find_by_name = AsyncMock(return_value=None)
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = SkillCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(user_id=str(uuid4()), payload={"name": "Python"}, uow=uow)
        assert result.is_success

    async def test_add_conflict(self):
        existing = Skill.create(user_id=uuid4(), name="Python")
        repo = MagicMock()
        repo.find_by_name = AsyncMock(return_value=existing)
        crud = SkillCrud(repo, MagicMock())
        uow = MagicMock(spec=UnitOfWork)
        result = await crud.add(user_id=str(uuid4()), payload={"name": "Python"}, uow=uow)
        assert result.is_failure


# --- Remaining CRUD classes (Certification / Course / Language / Achievement / Interest / ADR / Artifact)


class TestCertificationCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = CertificationCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"name": "AWS SA", "issuer": "AWS"}, uow=uow
        )
        assert result.is_success
        repo.add.assert_awaited_once()

    async def test_update_success(self):
        from src.universe.domain.entities import Certification

        entity = Certification.create(user_id=uuid4(), name="AWS SA", issuer="AWS")
        repo = MagicMock()
        repo.get = AsyncMock(return_value=entity)
        repo.update = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = CertificationCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.update(
            user_id=str(entity.user_id), entity_id=str(entity.id), patch={"name": "AWS Pro"}, uow=uow
        )
        assert result.is_success


class TestCourseCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = CourseCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"title": "RAG 101", "platform": "DL.AI"}, uow=uow
        )
        assert result.is_success


class TestLanguageCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = LanguageCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"code": "en", "name": "English", "level": "C1"}, uow=uow
        )
        assert result.is_success


class TestAchievementCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = AchievementCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"title": "Best paper", "achieved_on": "2024-06-01"}, uow=uow
        )
        assert result.is_success


class TestInterestCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = InterestCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"name": "RAG"}, uow=uow
        )
        assert result.is_success


class TestArchitectureDecisionCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        sched = MagicMock()
        sched.enqueue = AsyncMock()
        crud = ArchitectureDecisionCrud(repo, sched)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"title": "Use Postgres"}, uow=uow
        )
        assert result.is_success


class TestArtifactCrud:
    async def test_add_success(self):
        repo = MagicMock()
        repo.add = AsyncMock()
        crud = ArtifactCrud(repo, MagicMock())
        uow = MagicMock(spec=UnitOfWork)
        uow.add_event = MagicMock()
        result = await crud.add(
            user_id=str(uuid4()), payload={"type": "blog_post", "title": "Blog post", "url": "https://example.com"}, uow=uow
        )
        assert result.is_success
