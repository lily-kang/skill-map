"""Parse SR Learning Progression HTML files into structured JSON."""

import json
import re
from pathlib import Path
from html.parser import HTMLParser


class SkillHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}
        self.h1_text = ""
        self.is_focus_skill = False
        self._current_tag = None
        self._current_class = None
        self._capture_label = False
        self._capture_value = False
        self._current_label = None

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        cls = dict(attrs).get("class", "")
        self._current_class = cls
        if tag == "div" and cls == "field-label":
            self._capture_label = True
            self._current_label = ""
        elif tag == "div" and cls == "field-value":
            self._capture_value = True
            self.fields[self._current_label] = ""
        elif tag == "span" and "focus-badge" in cls:
            self.is_focus_skill = True

    def handle_endtag(self, tag):
        if tag == "div":
            self._capture_label = False
            self._capture_value = False

    def handle_data(self, data):
        if self._current_tag == "h1" or (self._current_tag == "span" and "focus-badge" in (self._current_class or "")):
            self.h1_text += data
        if self._capture_label:
            self._current_label = (self._current_label or "") + data
        elif self._capture_value and self._current_label:
            self.fields[self._current_label] += data


# Matches all forms found in HTML:
#   "Grade 1 - ...", "Grade Pre-K - ...", "Grade K - ..."
#   "Kindergarten - ...", "Pre-Kindergarten - ..."
GRADE_PATTERN = re.compile(
    r"(?=(?:Grade (?:Pre-K|\d+|K)|Pre-Kindergarten|(?<!Pre-)Kindergarten) - )"
)

GRADE_NORMALIZE = {
    "Kindergarten": "K",
    "Pre-Kindergarten": "Pre-K",
}


def parse_prerequisite_skills(text: str) -> list[dict]:
    if not text or not text.strip():
        return []
    parts = GRADE_PATTERN.split(text)
    results = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(
            r"(Grade (?:Pre-K|\d+|K)|Pre-Kindergarten|Kindergarten) - (.+)",
            part, re.DOTALL
        )
        if m:
            raw_grade = m.group(1)
            # Normalize: "Grade 3" -> "3", "Kindergarten" -> "K", etc.
            if raw_grade.startswith("Grade "):
                grade = raw_grade[6:]  # strip "Grade "
            else:
                grade = GRADE_NORMALIZE.get(raw_grade, raw_grade)
            results.append({"grade": grade, "description": m.group(2).strip()})
    return results


def parse_html_file(filepath: Path, grade_folder: str) -> dict:
    parser = SkillHTMLParser()
    parser.feed(filepath.read_text(encoding="utf-8"))

    fields = parser.fields
    filename = filepath.stem
    is_focus = filename.startswith("fs_")
    skill_code = filename.split(" - ")[0]
    if is_focus:
        skill_code = skill_code[3:]  # remove "fs_"

    h1_clean = parser.h1_text.replace("⚡ Focus Skill", "").strip()

    return {
        "skill_code": skill_code,
        "skill_name": fields.get("Short Skill Name", "").strip(),
        "full_description": h1_clean,
        "grade": grade_folder,
        "is_focus_skill": is_focus or parser.is_focus_skill,
        "skill_area": fields.get("Skill Area", "").strip(),
        "domain": fields.get("Domains", "").strip(),
        "domain_level_expectations": fields.get("Domain Level Expectations", "").strip(),
        "standard": fields.get("Standards", "").strip(),
        "prerequisite_skills": parse_prerequisite_skills(fields.get("Prerequisite Skills", "")),
        "ell_support": fields.get("ELL Support", "").strip() or None,
        "content_area_vocabulary": [
            v.strip() for v in fields.get("Content-Area Vocabulary", "").split(",") if v.strip()
        ] or None,
        "conceptual_knowledge": fields.get("Conceptual Knowledge", "").strip() or None,
        "linguistic_competencies": fields.get("Linguistic Competencies", "").strip() or None,
    }


def _skill_dict_from_crawl_item(item: dict, grade: str) -> dict:
    """Shared shape for K / Pre-K rows from _crawl_full.json."""
    f = item["fields"]
    return {
        "skill_code": item["skill_code"],
        "skill_name": f.get("Short Skill Name", item["skill_name"]).strip(),
        "full_description": item["full_description"],
        "grade": grade,
        "is_focus_skill": item["is_focus"],
        "skill_area": f.get("Skill Area", "").strip(),
        "domain": f.get("Domains", "").strip(),
        "domain_level_expectations": f.get("Domain Level Expectations", "").strip(),
        "standard": f.get("Standards", "").strip(),
        "prerequisite_skills": parse_prerequisite_skills(f.get("Prerequisite Skills", "")),
        "ell_support": f.get("ELL Support", "").strip() or None,
        "content_area_vocabulary": [
            v.strip() for v in f.get("Content-Area Vocabulary", "").split(",") if v.strip()
        ] or None,
        "conceptual_knowledge": f.get("Conceptual Knowledge", "").strip() or None,
        "linguistic_competencies": f.get("Linguistic Competencies", "").strip() or None,
    }


def parse_k_from_crawl(crawl_path: Path) -> list[dict]:
    """Build K grade skills from _crawl_full.json (not HTML files)."""
    crawl = json.loads(crawl_path.read_text(encoding="utf-8"))
    return [_skill_dict_from_crawl_item(item, "K") for item in crawl]


def parse_prek_from_crawl(crawl_path: Path) -> list[dict]:
    """Build Pre-K skills from Learning_Progression/Pre-K/_crawl_full.json."""
    crawl = json.loads(crawl_path.read_text(encoding="utf-8"))
    return [_skill_dict_from_crawl_item(item, "Pre-K") for item in crawl]


def main():
    base = Path(__file__).parent / "Learning_Progression"
    all_skills = []

    grade_order = {"Pre-K": -1, "K": 0}

    for grade_folder in sorted(base.iterdir()):
        if not grade_folder.is_dir():
            continue
        grade_name = grade_folder.name

        # K grade: use crawl JSON, not HTML files
        if grade_name == "K":
            crawl_path = grade_folder / "_crawl_full.json"
            if crawl_path.exists():
                k_skills = parse_k_from_crawl(crawl_path)
                all_skills.extend(k_skills)
                print(f"K grade: {len(k_skills)} skills from crawl JSON")
            else:
                print("WARNING: K/_crawl_full.json not found, skipping K grade")
            continue

        # Pre-K: prefer _crawl_full.json from crawl_prek_descriptions.py (same pattern as K)
        if grade_name == "Pre-K":
            crawl_path = grade_folder / "_crawl_full.json"
            if crawl_path.exists():
                pk_skills = parse_prek_from_crawl(crawl_path)
                all_skills.extend(pk_skills)
                print(f"Pre-K grade: {len(pk_skills)} skills from crawl JSON")
                continue

        for html_file in sorted(grade_folder.glob("*.html")):
            try:
                skill = parse_html_file(html_file, grade_name)
                all_skills.append(skill)
            except Exception as e:
                print(f"ERROR parsing {html_file}: {e}")

    # Sort by grade order
    all_skills.sort(key=lambda s: (
        grade_order.get(s["grade"], int(s["grade"]) if s["grade"].isdigit() else 99),
        s["skill_code"],
        s["skill_name"],
    ))

    output = Path(__file__).parent / "skills.json"
    output.write_text(json.dumps(all_skills, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Total: {len(all_skills)} skills -> {output}")

    # Quick validation
    k = [s for s in all_skills if s["grade"] == "K"]
    pk = [s for s in all_skills if s["grade"] == "Pre-K"]
    prereq_total = sum(len(s["prerequisite_skills"]) for s in all_skills)
    print(f"K grade: {len(k)}, Pre-K: {len(pk)}, Total prereq links: {prereq_total}")

    # Sample check
    grade1 = [s for s in all_skills if s["grade"] == "1" and s["prerequisite_skills"]]
    if grade1:
        sample = grade1[0]
        print(f"Grade 1 sample prereq: {sample['prerequisite_skills'][:2]}")


if __name__ == "__main__":
    main()
