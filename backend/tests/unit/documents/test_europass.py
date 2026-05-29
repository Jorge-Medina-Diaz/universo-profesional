"""Unit tests for the JSON Resume → Europass CV mapper (pure)."""
from __future__ import annotations

from src.documents.application.europass import _period, _split_name, to_europass


def test_split_name():
    assert _split_name("Jane Doe") == ("Jane", "Doe")
    assert _split_name("Jane Van Der Berg") == ("Jane", "Van Der Berg")
    assert _split_name("Madonna") == ("Madonna", "")
    assert _split_name(None) == ("", "")


def test_period_current_when_no_end():
    p = _period("2020-01", None)
    assert p["From"] == {"Year": 2020, "Month": 1}
    assert p.get("Current") is True
    assert "To" not in p


def test_period_with_end():
    p = _period("2018", "2022-06-30")
    assert p["From"] == {"Year": 2018}
    assert p["To"] == {"Year": 2022, "Month": 6, "Day": 30}
    assert "Current" not in p


def test_full_mapping_shape():
    resume = {
        "basics": {
            "name": "Jane Doe",
            "label": "Senior Engineer",
            "email": "jane@example.com",
            "summary": "Experienced dev.",
        },
        "work": [
            {
                "name": "Acme",
                "position": "Senior Engineer",
                "startDate": "2020-01",
                "endDate": None,
                "highlights": ["Shipped X"],
            }
        ],
        "education": [
            {"institution": "MIT", "studyType": "BSc", "area": "CS", "startDate": "2015"}
        ],
        "skills": [{"name": "Python"}, {"name": "FastAPI"}],
        "languages": [
            {"language": "Spanish", "fluency": "Native"},
            {"language": "English", "fluency": "C1"},
        ],
        "meta": {"language": "es"},
    }
    out = to_europass(resume)
    learner = out["SkillsPassport"]["LearnerInfo"]
    assert learner["Identification"]["PersonName"] == {"FirstName": "Jane", "Surname": "Doe"}
    assert learner["Identification"]["ContactInfo"]["Email"]["Contact"] == "jane@example.com"
    assert learner["Headline"]["Description"]["Label"] == "Senior Engineer"
    assert learner["WorkExperienceList"][0]["Employer"]["Name"] == "Acme"
    assert learner["WorkExperienceList"][0]["Period"]["Current"] is True
    assert learner["EducationList"][0]["Organisation"]["Name"] == "MIT"
    # Spanish is the mother tongue, English a foreign language
    ling = learner["Skills"]["Linguistic"]
    assert ling["MotherTongueList"][0]["Description"]["Label"] == "Spanish"
    assert ling["ForeignLanguageList"][0]["Description"]["Label"] == "English"
    assert "Python" in learner["Skills"]["Computer"]["Description"]["Label"]
    assert out["SkillsPassport"]["locale"] == "es"


def test_empty_resume_minimal():
    out = to_europass({})
    learner = out["SkillsPassport"]["LearnerInfo"]
    assert learner["Identification"]["PersonName"] == {"FirstName": "", "Surname": ""}
    assert "WorkExperienceList" not in learner
    assert "Skills" not in learner
