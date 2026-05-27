"""Unit tests for universe domain entity constructors (pure, no DB)."""
from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from src.shared.errors import ValidationError
from src.universe.domain.achievement import Achievement
from src.universe.domain.architecture_decision import ADR_STATUSES, ArchitectureDecision
from src.universe.domain.artifact import Artifact, _ARTIFACT_TYPES
from src.universe.domain.career import AreaStrength, CANONICAL_AREAS
from src.universe.domain.certification import Certification
from src.universe.domain.course import Course
from src.universe.domain.education import Education
from src.universe.domain.experience import Experience
from src.universe.domain.interest import Interest
from src.universe.domain.language import Language
from src.universe.domain.project import Project
from src.universe.domain.rubric_signal import SIGNAL_SECTION_KINDS, SIGNAL_STATUSES, UserRubricSignal
from src.universe.domain.skill import Skill
from src.universe.domain.skill_stack import SkillStack


UID = uuid4()


class TestSkill:
    def test_create_minimal(self):
        s = Skill.create(user_id=UID, name="Python")
        assert s.name == "Python"
        assert s.category == "hard"

    def test_create_with_level(self):
        s = Skill.create(user_id=UID, name="Python", level="expert")
        assert s.level == "expert"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Skill.create(user_id=UID, name="  ")

    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            Skill.create(user_id=UID, name="X", category="magic")

    def test_invalid_level_raises(self):
        with pytest.raises(ValidationError):
            Skill.create(user_id=UID, name="X", level="over9000")

    def test_embedding_text(self):
        s = Skill.create(user_id=UID, name="Rust", level="expert")
        assert "Rust" in s.embedding_text()


class TestEducation:
    def test_create(self):
        e = Education.create(user_id=UID, institution="MIT")
        assert e.institution == "MIT"

    def test_empty_institution_raises(self):
        with pytest.raises(ValidationError):
            Education.create(user_id=UID, institution="  ")

    def test_embedding_text(self):
        e = Education.create(user_id=UID, institution="MIT", degree="BS", field_of_study="CS", description="Desc")
        text = e.embedding_text()
        assert "MIT" in text
        assert "BS" in text
        assert "Desc" in text


class TestExperience:
    def test_create(self):
        ex = Experience.create(user_id=UID, organization="Google", role="SWE")
        assert ex.organization == "Google"
        assert ex.role == "SWE"

    def test_empty_org_raises(self):
        with pytest.raises(ValidationError):
            Experience.create(user_id=UID, organization="", role="X")

    def test_empty_role_raises(self):
        with pytest.raises(ValidationError):
            Experience.create(user_id=UID, organization="G", role="  ")

    def test_embedding_text(self):
        ex = Experience.create(user_id=UID, organization="G", role="Dev", description="build")
        assert "Dev" in ex.embedding_text()


class TestProject:
    def test_create(self):
        p = Project.create(user_id=UID, name="Foo")
        assert p.name == "Foo"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Project.create(user_id=UID, name="  ")

    def test_embedding_text(self):
        p = Project.create(user_id=UID, name="Foo", tech_stack=["py"], description="Desc", impact="High")
        assert "py" in p.embedding_text()
        assert "Desc" in p.embedding_text()
        assert "High" in p.embedding_text()


class TestArtifact:
    def test_create(self):
        a = Artifact.create(user_id=UID, type="blog_post", title="Post", url="http://x.com")
        assert a.type == "blog_post"

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            Artifact.create(user_id=UID, type="invalid", title="T", url="http://x.com")

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Artifact.create(user_id=UID, type="other", title="", url="http://x.com")

    def test_empty_url_raises(self):
        with pytest.raises(ValidationError):
            Artifact.create(user_id=UID, type="other", title="T", url="  ")

    def test_all_types(self):
        for t in _ARTIFACT_TYPES:
            a = Artifact.create(user_id=UID, type=t, title="X", url="http://x.com")
            assert a.type == t

    def test_embedding_text(self):
        a = Artifact.create(user_id=UID, type="blog_post", title="T", url="http://x.com")
        assert "T" in a.embedding_text()


class TestCertification:
    def test_create(self):
        c = Certification.create(user_id=UID, name="AWS")
        assert c.name == "AWS"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Certification.create(user_id=UID, name="  ")

    def test_embedding_text(self):
        c = Certification.create(user_id=UID, name="AWS", issuer="Amazon")
        assert "AWS" in c.embedding_text()


class TestCourse:
    def test_create(self):
        c = Course.create(user_id=UID, title="ML 101")
        assert c.title == "ML 101"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Course.create(user_id=UID, title="  ")

    def test_embedding_text(self):
        c = Course.create(user_id=UID, title="ML", platform="Coursera")
        assert "ML" in c.embedding_text()


class TestLanguage:
    def test_create(self):
        l = Language.create(user_id=UID, code="en", name="English", level="C1")
        assert l.code == "en"

    def test_invalid_code_raises(self):
        with pytest.raises(ValidationError):
            Language.create(user_id=UID, code="eng", name="English", level="C1")

    def test_invalid_level_raises(self):
        with pytest.raises(ValidationError):
            Language.create(user_id=UID, code="en", name="English", level="Z9")

    def test_embedding_text(self):
        l = Language.create(user_id=UID, code="en", name="English", level="C1")
        assert "C1" in l.embedding_text()


class TestInterest:
    def test_create(self):
        i = Interest.create(user_id=UID, name="Hiking")
        assert i.name == "Hiking"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Interest.create(user_id=UID, name="  ")

    def test_embedding_text(self):
        i = Interest.create(user_id=UID, name="Hiking")
        assert i.embedding_text() == "Hiking"


class TestAchievement:
    def test_create(self):
        a = Achievement.create(user_id=UID, title="Won prize")
        assert a.title == "Won prize"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Achievement.create(user_id=UID, title="  ")

    def test_embedding_text(self):
        a = Achievement.create(user_id=UID, title="Prize", description="Desc")
        assert "Prize" in a.embedding_text()


class TestArchitectureDecision:
    def test_create(self):
        ad = ArchitectureDecision.create(user_id=UID, title="Use Postgres")
        assert ad.title == "Use Postgres"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            ArchitectureDecision.create(user_id=UID, title="  ")

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            ArchitectureDecision.create(user_id=UID, title="X", status="draft")

    def test_all_statuses(self):
        for st in ADR_STATUSES:
            ad = ArchitectureDecision.create(user_id=UID, title="X", status=st)
            assert ad.status == st

    def test_embedding_text(self):
        ad = ArchitectureDecision.create(user_id=UID, title="T", context="Ctx")
        assert "T" in ad.embedding_text()


class TestAreaStrength:
    def test_create(self):
        a = AreaStrength.create(user_id=UID, area="backend")
        assert a.area == "backend"

    def test_invalid_area_raises(self):
        with pytest.raises(ValidationError):
            AreaStrength.create(user_id=UID, area="magic")

    def test_all_areas(self):
        for area in CANONICAL_AREAS:
            a = AreaStrength.create(user_id=UID, area=area)
            assert a.area == area


class TestSkillStack:
    def test_create(self):
        ss = SkillStack.create(user_id=UID, name="Web", slug="web", area="frontend")
        assert ss.name == "Web"
        assert ss.area == "frontend"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            SkillStack.create(user_id=UID, name="", slug="x", area="backend")

    def test_empty_slug_raises(self):
        with pytest.raises(ValidationError):
            SkillStack.create(user_id=UID, name="X", slug="  ", area="backend")

    def test_invalid_area_raises(self):
        with pytest.raises(ValidationError):
            SkillStack.create(user_id=UID, name="X", slug="x", area="bad")


class TestUserRubricSignal:
    def test_create(self):
        r = UserRubricSignal.create(user_id=UID, rubric_chunk_id=uuid4(), section_kind="signals", status="aspire")
        assert r.status == "aspire"

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            UserRubricSignal.create(user_id=UID, rubric_chunk_id=uuid4(), section_kind="signals", status="bad")

    def test_invalid_section_raises(self):
        with pytest.raises(ValidationError):
            UserRubricSignal.create(user_id=UID, rubric_chunk_id=uuid4(), section_kind="bad", status="aspire")

    def test_all_combinations(self):
        for status in SIGNAL_STATUSES:
            for section in SIGNAL_SECTION_KINDS:
                r = UserRubricSignal.create(user_id=UID, rubric_chunk_id=uuid4(), section_kind=section, status=status)
                assert r.status == status
                assert r.section_kind == section
