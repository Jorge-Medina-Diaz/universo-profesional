"""Unit tests for import_router helpers — pure logic + mocked IO."""
from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock, MagicMock

from src.shared.result import Success
from src.universe.interfaces.api.import_router import (
    _find_csv_files,
    _parse_li_date,
    _parse_li_educations,
    _parse_li_experiences,
    _parse_li_skills,
    import_json_resume,
)


def _make_zip(contents: dict[str, str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in contents.items():
            zf.writestr(name, data)
    buf.seek(0)
    return zipfile.ZipFile(buf)


class TestFindCsvFiles:
    def test_finds_all_three(self):
        zf = _make_zip({"Positions.csv": "", "Education.csv": "", "Skills.csv": ""})
        found = _find_csv_files(zf)
        assert found == {"positions": "Positions.csv", "education": "Education.csv", "skills": "Skills.csv"}

    def test_missing_skills(self):
        zf = _make_zip({"Positions.csv": "", "Education.csv": ""})
        found = _find_csv_files(zf)
        assert found["skills"] is None
        assert found["positions"] is not None

    def test_case_insensitive(self):
        zf = _make_zip({"positions.csv": "", "education.csv": "", "skills.csv": ""})
        found = _find_csv_files(zf)
        assert found == {"positions": "positions.csv", "education": "education.csv", "skills": "skills.csv"}


class TestParseLiDate:
    def test_none_returns_none(self):
        assert _parse_li_date(None) is None

    def test_empty_returns_none(self):
        assert _parse_li_date("") is None

    def test_mon_yyyy(self):
        assert _parse_li_date("Jan 2020") == "2020-01-01"
        assert _parse_li_date("Dec 2019") == "2019-12-01"

    def test_falls_through(self):
        assert _parse_li_date("2020-01-15") == "2020-01-15"


class TestParseLiExperiences:
    async def test_parses_rows(self):
        csv_data = "Company Name,Title,Description,Started On,Finished On\nAcme,Engineer,dev,Jan 2020,Dec 2021\n"
        zf = _make_zip({"Positions.csv": csv_data})
        exp_uc = MagicMock()
        exp_uc.add = AsyncMock(return_value=Success(None))
        count = await _parse_li_experiences(zf, "Positions.csv", "user-1", exp_uc, MagicMock())
        assert count == 1
        exp_uc.add.assert_awaited_once()

    async def test_skips_missing_org_or_role(self):
        csv_data = "Company Name,Title,Description,Started On,Finished On\n,Engineer,dev,Jan 2020,\nAcme,,dev,Jan 2020,\n"
        zf = _make_zip({"Positions.csv": csv_data})
        exp_uc = MagicMock()
        exp_uc.add = AsyncMock(return_value=Success(None))
        count = await _parse_li_experiences(zf, "Positions.csv", "user-1", exp_uc, MagicMock())
        assert count == 0

    async def test_current_when_no_end_date(self):
        csv_data = "Company Name,Title,Description,Started On,Finished On\nAcme,Engineer,dev,Jan 2020,\n"
        zf = _make_zip({"Positions.csv": csv_data})
        exp_uc = MagicMock()
        exp_uc.add = AsyncMock(return_value=Success(None))
        await _parse_li_experiences(zf, "Positions.csv", "user-1", exp_uc, MagicMock())
        payload = exp_uc.add.await_args.kwargs["payload"]
        assert payload["is_current"] is True
        assert payload["end_date"] is None


class TestParseLiEducations:
    async def test_parses_rows(self):
        csv_data = "School Name,Degree Name,Notes,Start Date,End Date\nUSE,BSc,CS,2018,2022\n"
        zf = _make_zip({"Education.csv": csv_data})
        edu_uc = MagicMock()
        edu_uc.add = AsyncMock(return_value=Success(None))
        count = await _parse_li_educations(zf, "Education.csv", "user-1", edu_uc, MagicMock())
        assert count == 1

    async def test_skips_missing_institution(self):
        csv_data = "School Name,Degree Name,Notes,Start Date,End Date\n,BSc,CS,2018,2022\n"
        zf = _make_zip({"Education.csv": csv_data})
        edu_uc = MagicMock()
        edu_uc.add = AsyncMock(return_value=Success(None))
        count = await _parse_li_educations(zf, "Education.csv", "user-1", edu_uc, MagicMock())
        assert count == 0


class TestParseLiSkills:
    async def test_parses_rows(self):
        csv_data = "Name\nPython\nPostgreSQL\n"
        zf = _make_zip({"Skills.csv": csv_data})
        skill_uc = MagicMock()
        skill_uc.add = AsyncMock(return_value=Success(None))
        count = await _parse_li_skills(zf, "Skills.csv", "user-1", skill_uc, MagicMock())
        assert count == 2

    async def test_skips_empty_name(self):
        csv_data = "Name\n\nPython\n"
        zf = _make_zip({"Skills.csv": csv_data})
        skill_uc = MagicMock()
        skill_uc.add = AsyncMock(return_value=Success(None))
        count = await _parse_li_skills(zf, "Skills.csv", "user-1", skill_uc, MagicMock())
        assert count == 1


class TestImportJsonResume:
    async def test_imports_work_education_skills(self):
        session = MagicMock()
        session.commit = AsyncMock()
        uow = MagicMock()
        uow.commit = AsyncMock()

        edu_uc = MagicMock()
        edu_uc.add = AsyncMock(return_value=Success(None))
        exp_uc = MagicMock()
        exp_uc.add = AsyncMock(return_value=Success(None))
        skill_uc = MagicMock()
        skill_uc.add = AsyncMock(return_value=Success(None))

        body = {
            "work": [
                {"name": "Acme", "position": "Dev", "summary": "code", "startDate": "2020-01", "endDate": "2021-01", "highlights": ["ship"]}
            ],
            "education": [
                {"institution": "USE", "studyType": "BSc", "area": "CS", "startDate": "2015", "endDate": "2019"}
            ],
            "skills": [
                {"name": "Python", "level": "Expert"}
            ],
        }

        # Need to mock unit_of_work context manager
        from src.universe.interfaces.api import import_router as ir
        orig_uow = ir.unit_of_work
        ir.unit_of_work = MagicMock()
        ir.unit_of_work.return_value.__aenter__ = AsyncMock(return_value=uow)
        ir.unit_of_work.return_value.__aexit__ = AsyncMock(return_value=None)

        try:
            result = await import_json_resume("user-1", edu_uc, exp_uc, skill_uc, session, body)
            assert result == {"educations": 1, "experiences": 1, "skills": 1}
        finally:
            ir.unit_of_work = orig_uow

    async def test_requires_body(self):
        session = MagicMock()
        edu_uc = MagicMock()
        exp_uc = MagicMock()
        skill_uc = MagicMock()
        result = await import_json_resume("user-1", edu_uc, exp_uc, skill_uc, session, None)
        assert result == {"errors": ["body required"]}
