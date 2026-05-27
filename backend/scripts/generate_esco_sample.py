"""Generate a minimal ESCO sample dataset for offline dev (~500 rows total)."""
from __future__ import annotations

import csv
import random
from pathlib import Path

random.seed(42)

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "esco_sample"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# --- ISCO groups (40) ---
isco_groups = []
for i in range(1, 41):
    code = f"{i:02d}"
    label = f"ISCO Group {code}"
    uri = f"http://data.europa.eu/esco/isco/C{code}"
    isco_groups.append({"conceptUri": uri, "code": code, "preferredLabel": label})

for suffix, fname in [("_en", "ISCOGroups_en.csv"), ("_es", "ISCOGroups_es.csv")]:
    with open(SAMPLE_DIR / fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["conceptUri", "code", "preferredLabel"])
        writer.writeheader()
        for g in isco_groups:
            row = dict(g)
            if suffix == "_es":
                row["preferredLabel"] = row["preferredLabel"] + " (ES)"
            writer.writerow(row)

# --- Occupations (200) ---
occupations = []
for i in range(1, 201):
    uri = f"http://data.europa.eu/esco/occupation/{i:08d}"
    label = f"Occupation {i}"
    alt = f"Alt occupation {i}\nSecondary title {i}" if i % 3 == 0 else ""
    desc = f"Description for occupation {i}. Performs tasks related to field {i}."
    isco = random.choice(isco_groups)["code"]  # noqa: S311
    occupations.append(
        {
            "conceptUri": uri,
            "preferredLabel": label,
            "altLabels": alt,
            "description": desc,
            "iscoGroup": isco,
        }
    )

for suffix, fname in [("_en", "occupations_en.csv"), ("_es", "occupations_es.csv")]:
    with open(SAMPLE_DIR / fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["conceptUri", "preferredLabel", "altLabels", "description", "iscoGroup"]
        )
        writer.writeheader()
        for occ in occupations:
            row = dict(occ)
            if suffix == "_es":
                row["preferredLabel"] = row["preferredLabel"] + " (ES)"
                row["description"] = row["description"] + " [ES]"
            writer.writerow(row)

# --- Skills (300) ---
skills = []
for i in range(1, 301):
    uri = f"http://data.europa.eu/esco/skill/{i:08d}"
    label = f"Skill {i}"
    alt = f"Alt skill {i}\nSynonym {i}" if i % 4 == 0 else ""
    desc = f"Description for skill {i}. Ability to perform task {i}."
    stype = random.choice(["knowledge", "skill", "attitude"])  # noqa: S311
    skills.append(
        {
            "conceptUri": uri,
            "preferredLabel": label,
            "altLabels": alt,
            "description": desc,
            "skillType": stype,
        }
    )

for suffix, fname in [("_en", "skills_en.csv"), ("_es", "skills_es.csv")]:
    with open(SAMPLE_DIR / fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["conceptUri", "preferredLabel", "altLabels", "description", "skillType"]
        )
        writer.writeheader()
        for sk in skills:
            row = dict(sk)
            if suffix == "_es":
                row["preferredLabel"] = row["preferredLabel"] + " (ES)"
                row["description"] = row["description"] + " [ES]"
            writer.writerow(row)

# --- Occupation x Skill relations ---
relations = []
for occ in occupations:
    # 1-3 skills per occupation
    for sk in random.sample(skills, k=random.randint(1, 3)):  # noqa: S311
        relations.append(
            {
                "occupationUri": occ["conceptUri"],
                "skillUri": sk["conceptUri"],
                "relationType": random.choice(["essential", "optional"]),  # noqa: S311
            }
        )

with open(SAMPLE_DIR / "occupationSkillRelations.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["occupationUri", "skillUri", "relationType"])
    writer.writeheader()
    writer.writerows(relations)

# --- Broader relations (small trees) ---
broader_occ = []
for i, occ in enumerate(occupations):
    if i > 0 and i % 5 == 0:
        broader_occ.append(
            {"conceptUri": occ["conceptUri"], "broaderUri": occupations[i - 5]["conceptUri"]}
        )

with open(SAMPLE_DIR / "broaderRelationsOccPillar.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["conceptUri", "broaderUri"])
    writer.writeheader()
    writer.writerows(broader_occ)

broader_skill = []
for i, sk in enumerate(skills):
    if i > 0 and i % 7 == 0:
        broader_skill.append(
            {"conceptUri": sk["conceptUri"], "broaderUri": skills[i - 7]["conceptUri"]}
        )

with open(SAMPLE_DIR / "broaderRelationsSkillPillar.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["conceptUri", "broaderUri"])
    writer.writeheader()
    writer.writerows(broader_skill)

# --- skillSkillRelations.csv (optional, ignored by loader but nice to have) ---
skill_skill = []
for i, sk in enumerate(skills):
    if i > 0 and i % 10 == 0:
        skill_skill.append(
            {"conceptUri": sk["conceptUri"], "relatedUri": skills[i - 10]["conceptUri"]}
        )

with open(SAMPLE_DIR / "skillSkillRelations.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["conceptUri", "relatedUri"])
    writer.writeheader()
    writer.writerows(skill_skill)

print(f"Sample ESCO dataset written to {SAMPLE_DIR}")
print(
    f"  ISCOGroups: {len(isco_groups)}, Occupations: {len(occupations)}, Skills: {len(skills)}, "
    f"Relations: {len(relations)}"
)
