"""Map a JSON Resume (`content_json`) to the Europass CV JSON model.

The CV generator already produces JSON Resume (jsonresume.org). Europass is the
EU's standardised CV model — its document is rooted at
``SkillsPassport > LearnerInfo`` with Identification / Headline / WorkExperience
/ Education / Skills sections. This is a pure, deterministic projection so it's
trivially testable and identical across the REST endpoint and any future use.

We map only fields we can ground from JSON Resume; absent fields are omitted
rather than invented.
"""
from __future__ import annotations

from typing import Any

_EUROPASS_NS = "http://europass.cedefop.europa.eu/Europass/V3.0"


def _split_name(full: str | None) -> tuple[str, str]:
    if not full:
        return "", ""
    parts = full.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _period(start: str | None, end: str | None) -> dict[str, Any]:
    """JSON Resume dates ('YYYY', 'YYYY-MM', 'YYYY-MM-DD') → Europass Period."""

    def part(d: str | None) -> dict[str, int] | None:
        if not d:
            return None
        bits = str(d).split("-")
        out: dict[str, int] = {}
        try:
            out["Year"] = int(bits[0])
            if len(bits) > 1:
                out["Month"] = int(bits[1])
            if len(bits) > 2:
                out["Day"] = int(bits[2])
        except (ValueError, IndexError):
            return None
        return out or None

    period: dict[str, Any] = {}
    if (frm := part(start)) is not None:
        period["From"] = frm
    if end:
        if (to := part(end)) is not None:
            period["To"] = to
    else:
        period["Current"] = True
    return period


def to_europass(content_json: dict[str, Any]) -> dict[str, Any]:
    """Project a JSON Resume object onto the Europass CV JSON model."""
    basics = content_json.get("basics", {}) or {}
    first, surname = _split_name(basics.get("name"))

    identification: dict[str, Any] = {
        "PersonName": {"FirstName": first, "Surname": surname},
    }
    contact: dict[str, Any] = {}
    if basics.get("email"):
        contact["Email"] = {"Contact": basics["email"]}
    if basics.get("phone"):
        contact["Telephone"] = [{"Contact": basics["phone"]}]
    if contact:
        identification["ContactInfo"] = contact

    learner: dict[str, Any] = {"Identification": identification}

    if basics.get("label") or basics.get("summary"):
        learner["Headline"] = {
            "Type": {"Code": "position", "Label": "Position applied for"},
            "Description": {"Label": basics.get("label") or ""},
        }
    if basics.get("summary"):
        learner["About"] = {"Label": basics["summary"]}

    work = content_json.get("work") or []
    if work:
        learner["WorkExperienceList"] = [
            {
                "Period": _period(w.get("startDate"), w.get("endDate")),
                "Position": {"Label": w.get("position") or ""},
                "Activities": w.get("summary")
                or "\n".join(w.get("highlights", []) or []),
                "Employer": {"Name": w.get("name") or "", "ContactInfo": {}},
            }
            for w in work
        ]

    education = content_json.get("education") or []
    if education:
        learner["EducationList"] = [
            {
                "Period": _period(e.get("startDate"), e.get("endDate")),
                "Title": " — ".join(
                    filter(None, [e.get("studyType"), e.get("area")])
                ),
                "Organisation": {"Name": e.get("institution") or ""},
            }
            for e in education
        ]

    skills_block: dict[str, Any] = {}
    languages = content_json.get("languages") or []
    if languages:
        mother: list[dict[str, Any]] = []
        foreign: list[dict[str, Any]] = []
        for lang in languages:
            entry = {"Description": {"Label": lang.get("language") or ""}}
            fluency = (lang.get("fluency") or "").lower()
            if "nativ" in fluency or "mother" in fluency or "materna" in fluency:
                mother.append(entry)
            else:
                foreign.append(
                    {**entry, "ProficiencyLevel": {"_self": lang.get("fluency") or ""}}
                )
        linguistic: dict[str, Any] = {}
        if mother:
            linguistic["MotherTongueList"] = mother
        if foreign:
            linguistic["ForeignLanguageList"] = foreign
        if linguistic:
            skills_block["Linguistic"] = linguistic

    tech_skills = content_json.get("skills") or []
    if tech_skills:
        skills_block["Computer"] = {
            "Description": {
                "Label": ", ".join(s.get("name", "") for s in tech_skills if s.get("name"))
            }
        }

    if skills_block:
        learner["Skills"] = skills_block

    return {
        "SkillsPassport": {
            "locale": (content_json.get("meta", {}) or {}).get("language", "en"),
            "DocumentInfo": {
                "DocumentType": "ECV",
                "XSDVersion": "V3.0",
                "Generator": "cvs-saas",
            },
            "LearnerInfo": learner,
            "@xmlns": _EUROPASS_NS,
        }
    }
