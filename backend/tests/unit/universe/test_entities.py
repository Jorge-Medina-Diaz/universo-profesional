"""Unit tests for universe domain entities — create() validation + embedding_text."""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.shared.errors import ValidationError
from src.universe.domain.entities import (
    Achievement,
    ArchitectureDecision,
    AreaStrength,
    Artifact,
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


class TestEducation:
    def test_create_valid(self):
        e = Education.create(user_id=uuid4(), institution="USE")
        assert e.institution == "USE"

    def test_create_empty_institution_raises(self):
        with pytest.raises(ValidationError):
            Education.create(user_id=uuid4(), institution="  ")

    def test_embedding_text(self):
        e = Education.create(user_id=uuid4(), institution="USE", degree="BSc", field_of_study="CS")
        text = e.embedding_text()
        assert "USE" in text
        assert "BSc" in text


class TestExperience:
    def test_create_valid(self):
        e = Experience.create(user_id=uuid4(), organization="Acme", role="Dev")
        assert e.organization == "Acme"

    def test_create_missing_org_raises(self):
        with pytest.raises(ValidationError):
            Experience.create(user_id=uuid4(), organization="", role="Dev")

    def test_create_missing_role_raises(self):
        with pytest.raises(ValidationError):
            Experience.create(user_id=uuid4(), organization="Acme", role="  ")

    def test_embedding_text(self):
        e = Experience.create(user_id=uuid4(), organization="Acme", role="Dev", description="code")
        text = e.embedding_text()
        assert "Dev" in text
        assert "Acme" in text


class TestProject:
    def test_create_valid(self):
        p = Project.create(user_id=uuid4(), name="demo")
        assert p.name == "demo"

    def test_create_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Project.create(user_id=uuid4(), name="")

    def test_embedding_text(self):
        p = Project.create(user_id=uuid4(), name="demo", description="app", tech_stack=["python"])
        text = p.embedding_text()
        assert "demo" in text
        assert "python" in text


class TestSkill:
    def test_create_valid(self):
        s = Skill.create(user_id=uuid4(), name="Python")
        assert s.name == "Python"
        assert s.category == "hard"

    def test_create_invalid_category(self):
        with pytest.raises(ValidationError):
            Skill.create(user_id=uuid4(), name="Python", category="magic")

    def test_create_invalid_level(self):
        with pytest.raises(ValidationError):
            Skill.create(user_id=uuid4(), name="Python", level="ninja")

    def test_embedding_text(self):
        s = Skill.create(user_id=uuid4(), name="Python", category="hard", level="expert")
        assert "Python" in s.embedding_text()


class TestCertification:
    def test_create_valid(self):
        c = Certification.create(user_id=uuid4(), name="AWS")
        assert c.name == "AWS"

    def test_create_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Certification.create(user_id=uuid4(), name="  ")


class TestCourse:
    def test_create_valid(self):
        c = Course.create(user_id=uuid4(), title="RAG 101")
        assert c.title == "RAG 101"

    def test_create_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Course.create(user_id=uuid4(), title="")


class TestLanguage:
    def test_create_valid(self):
        l = Language.create(user_id=uuid4(), code="en", name="English", level="C1")
        assert l.code == "en"

    def test_create_invalid_code_raises(self):
        with pytest.raises(ValidationError):
            Language.create(user_id=uuid4(), code="eng", name="English", level="C1")

    def test_create_invalid_level_raises(self):
        with pytest.raises(ValidationError):
            Language.create(user_id=uuid4(), code="en", name="English", level="Z9")


class TestAchievement:
    def test_create_valid(self):
        a = Achievement.create(user_id=uuid4(), title="Best Paper")
        assert a.title == "Best Paper"

    def test_create_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Achievement.create(user_id=uuid4(), title="")


class TestInterest:
    def test_create_valid(self):
        i = Interest.create(user_id=uuid4(), name="RAG")
        assert i.name == "RAG"

    def test_create_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Interest.create(user_id=uuid4(), name="  ")


class TestAreaStrength:
    def test_create_valid(self):
        a = AreaStrength.create(user_id=uuid4(), area="backend")
        assert a.area == "backend"

    def test_create_invalid_area_raises(self):
        with pytest.raises(ValidationError):
            AreaStrength.create(user_id=uuid4(), area="magic")


class TestArtifact:
    def test_create_valid(self):
        a = Artifact.create(user_id=uuid4(), type="talk", title="Talk", url="https://x.com")
        assert a.type == "talk"

    def test_create_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            Artifact.create(user_id=uuid4(), type="dance", title="D", url="https://x.com")

    def test_create_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Artifact.create(user_id=uuid4(), type="talk", title="", url="https://x.com")

    def test_create_empty_url_raises(self):
        with pytest.raises(ValidationError):
            Artifact.create(user_id=uuid4(), type="talk", title="T", url="  ")


class TestSkillStack:
    def test_create_valid(self):
        s = SkillStack.create(user_id=uuid4(), name="Web", slug="web", area="frontend")
        assert s.name == "Web"

    def test_create_empty_name_raises(self):
        with pytest.raises(ValidationError):
            SkillStack.create(user_id=uuid4(), name="", slug="web", area="frontend")

    def test_create_invalid_area_raises(self):
        with pytest.raises(ValidationError):
            SkillStack.create(user_id=uuid4(), name="Web", slug="web", area="magic")


class TestUserRubricSignal:
    def test_create_valid(self):
        s = UserRubricSignal.create(
            user_id=uuid4(), rubric_chunk_id=uuid4(), section_kind="signals", status="aspire"
        )
        assert s.status == "aspire"

    def test_create_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            UserRubricSignal.create(
                user_id=uuid4(), rubric_chunk_id=uuid4(), section_kind="signals", status="magic"
            )

    def test_create_invalid_section_raises(self):
        with pytest.raises(ValidationError):
            UserRubricSignal.create(
                user_id=uuid4(), rubric_chunk_id=uuid4(), section_kind="magic", status="aspire"
            )


class TestCertificationEmbedding:
    def test_embedding_text(self):
        c = Certification.create(user_id=uuid4(), name="AWS", issuer="Amazon")
        assert "AWS" in c.embedding_text()


class TestCourseEmbedding:
    def test_embedding_text(self):
        c = Course.create(user_id=uuid4(), title="RAG", platform="DLAI")
        assert "RAG" in c.embedding_text()


class TestLanguageEmbedding:
    def test_embedding_text(self):
        l = Language.create(user_id=uuid4(), code="en", name="English", level="C1")
        assert "English" in l.embedding_text()


class TestAchievementEmbedding:
    def test_embedding_text(self):
        a = Achievement.create(user_id=uuid4(), title="Best", description="Paper")
        assert "Best" in a.embedding_text()


class TestInterestEmbedding:
    def test_embedding_text(self):
        i = Interest.create(user_id=uuid4(), name="RAG")
        assert i.embedding_text() == "RAG"


class TestArtifactEmbedding:
    def test_embedding_text(self):
        a = Artifact.create(user_id=uuid4(), type="talk", title="T", url="https://x.com")
        assert "talk" in a.embedding_text()


class TestArchitectureDecision:
    def test_create_valid(self):
        a = ArchitectureDecision.create(user_id=uuid4(), title="ADR-1")
        assert a.title == "ADR-1"

    def test_create_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            ArchitectureDecision.create(user_id=uuid4(), title="ADR-1", status="magic")

    def test_embedding_text(self):
        a = ArchitectureDecision.create(user_id=uuid4(), title="ADR-1", context="ctx", decision="go")
        assert "ADR-1" in a.embedding_text()
