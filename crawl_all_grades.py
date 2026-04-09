"""Crawl skill details for all grades (1-12) from Renaissance LP.

Logs in once, then for each grade: selects it, opens Skill Details,
navigates to the first skill, and iterates through all skills.

Usage:
  1) Chrome on port 9222
  2) python crawl_all_grades.py              # all grades 1-12
  3) python crawl_all_grades.py 3 5 7        # specific grades only
  4) python crawl_all_grades.py Pre-K K 1    # any grade label
"""

import sys
import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

EDUCATOR_ENTRY = "https://global-zone60.renaissance-go.com/educatorportal/entry?t=rpna32xu"
LP_URL = "https://zone60-educator.renaissance-go.com/record-book/star/skill-recommendations/browselearningprogression"
USERNAME = "polyar"
PASSWORD = "sodium7965@"
BASE_DIR = Path(__file__).parent / "Learning_Progression"

ALL_GRADES = ["Pre-K", "K"] + [str(i) for i in range(1, 13)]

# --------------- JS snippets ---------------

JS_HAS_RECORD_BOOK = '''
    const h = document.querySelector("record-book");
    return !!(h && h.shadowRoot);
'''

JS_SELECT_GRADE = '''
    const grade = arguments[0];
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return "no-record-book";
    const rb = host.shadowRoot;
    const btns = rb.querySelectorAll("button.ren-btn");
    for (const b of btns) {
        if (b.textContent.trim() === grade) {
            b.click();
            return "clicked";
        }
    }
    return "not-found";
'''

JS_CLICK_SKILL_DETAILS = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return "no-record-book";
    const rb = host.shadowRoot;
    const spans = rb.querySelectorAll("span.ren-link");
    for (const s of spans) {
        if (s.textContent.trim() === "Skill Details") {
            s.click();
            return "clicked";
        }
    }
    return "not-found";
'''

JS_HAS_INFO_LIST = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return false;
    const rb = host.shadowRoot;
    return !!(rb.querySelector(".info-list") || rb.querySelector(".single-skill-view"));
'''

JS_EXTRACT = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return null;
    const rb = host.shadowRoot;
    const infoList = rb.querySelector(".single-skill-view.info-list, .info-list");
    if (!infoList) return null;

    let fullDesc = "";
    let el = infoList.previousElementSibling;
    while (el) {
        if (el.tagName === "DIV" && el.textContent.trim().length > 5 &&
            !el.textContent.includes("View Skill") && !el.textContent.includes("Short Skill Name")) {
            fullDesc = el.textContent.trim();
            break;
        }
        el = el.previousElementSibling;
    }

    const fullText = infoList.textContent;
    const knownFields = [
        "Short Skill Name", "Skill Area", "Domains", "Domain Level Expectations",
        "Standards", "Prerequisite Skills", "ELL Support", "Content-Area Vocabulary",
        "Conceptual Knowledge", "Linguistic Competencies"
    ];
    const fields = {};
    for (let i = 0; i < knownFields.length; i++) {
        const field = knownFields[i];
        const idx = fullText.indexOf(field);
        if (idx === -1) continue;
        const start = idx + field.length;
        let end = fullText.length;
        for (let j = 0; j < knownFields.length; j++) {
            if (j === i) continue;
            const nextIdx = fullText.indexOf(knownFields[j], start);
            if (nextIdx > start && nextIdx < end) end = nextIdx;
        }
        fields[field] = fullText.substring(start, end).trim();
    }

    const isFocus = !!(rb.querySelector(".focus-badge, [class*='focus-badge']")) ||
        fullText.includes("ELL Support") || fullText.includes("Conceptual Knowledge");

    return { fullDesc, fields, isFocus };
'''

JS_NEXT = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return false;
    const rb = host.shadowRoot;
    const links = rb.querySelectorAll("a.skill-nav-option");
    for (const l of links) {
        if (l.textContent.includes("Next") && !l.classList.contains("disabled")) {
            l.click(); return true;
        }
    }
    return false;
'''

JS_PREV = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return false;
    const rb = host.shadowRoot;
    const links = rb.querySelectorAll("a.skill-nav-option");
    for (const l of links) {
        if (l.textContent.includes("Prev") && !l.classList.contains("disabled")) {
            l.click(); return true;
        }
    }
    return false;
'''

# JS to go back from detail view to the skill list
JS_CLOSE_DETAIL = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return false;
    const rb = host.shadowRoot;
    const btns = rb.querySelectorAll("button.skill-nav-option");
    for (const b of btns) {
        if (b.textContent.trim() === "Close") {
            b.click(); return true;
        }
    }
    return false;
'''

# --------------- helpers ---------------


def create_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    return webdriver.Chrome(options=opts)


def wait_for_record_book(driver, timeout_sec=120):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if driver.execute_script(JS_HAS_RECORD_BOOK):
            return True
        time.sleep(2)
    return False


def login(driver):
    wait = WebDriverWait(driver, 30)
    print("Logging in...")
    driver.get(EDUCATOR_ENTRY)
    time.sleep(5)

    if not driver.find_elements(By.CSS_SELECTOR, "input[type='password']"):
        print("  Already logged in.")
        return

    username_input = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='text'], input[name='username'], input[name='userName'], #username, #userName")
    ))
    username_input.clear()
    username_input.send_keys(USERNAME)

    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.clear()
    password_input.send_keys(PASSWORD)

    submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    submit.click()
    time.sleep(10)
    print("  Done.")


def navigate_to_lp(driver):
    print("Navigating to LP...")
    driver.get(LP_URL)
    time.sleep(10)
    if not wait_for_record_book(driver, timeout_sec=120):
        raise SystemExit("record-book not found.")
    print("  LP loaded.")


def select_grade(driver, grade):
    """Select a grade and wait for skill list to load."""
    result = driver.execute_script(JS_SELECT_GRADE, grade)
    if result != "clicked":
        return False
    time.sleep(5)
    return True


def open_skill_details(driver):
    """Click the first 'Skill Details' link and wait for detail view."""
    result = driver.execute_script(JS_CLICK_SKILL_DETAILS)
    if result != "clicked":
        return False
    for _ in range(15):
        if driver.execute_script(JS_HAS_INFO_LIST):
            return True
        time.sleep(2)
    return False


def go_to_first_skill(driver):
    while True:
        has_prev = driver.execute_script(JS_PREV)
        if not has_prev:
            break
        time.sleep(0.5)
    time.sleep(1)


def close_detail_view(driver):
    driver.execute_script(JS_CLOSE_DETAIL)
    time.sleep(3)


def crawl_grade(driver, grade):
    """Crawl all skills for a single grade. Returns list of skill dicts."""
    results = []
    count = 0

    while True:
        time.sleep(1.5)
        data = driver.execute_script(JS_EXTRACT)
        if not data:
            # retry once
            time.sleep(3)
            data = driver.execute_script(JS_EXTRACT)
            if not data:
                print(f"    Could not extract skill {count+1}. Stopping.")
                break

        fields = data["fields"]
        standard = fields.get("Standards", "")
        skill_code = standard.split(" - ")[0].strip() if " - " in standard else f"UNK_{count}"
        short_name = fields.get("Short Skill Name", "")
        full_desc = data["fullDesc"]

        tag = "FS" if data["isFocus"] else "  "
        print(f"  [{count+1:3d}] {tag} {skill_code:25s} | {short_name[:40]}")

        results.append({
            "skill_code": skill_code,
            "skill_name": short_name,
            "full_description": full_desc,
            "standard": standard,
            "is_focus": data["isFocus"],
            "fields": fields,
        })
        count += 1

        has_next = driver.execute_script(JS_NEXT)
        if not has_next:
            break
        time.sleep(0.5)

    return results


def grade_dir_name(grade):
    """Map grade label to folder name (e.g. '1' -> '1', 'Pre-K' -> 'Pre-K')."""
    return grade


# --------------- main ---------------

def main():
    # Parse grade arguments
    if len(sys.argv) > 1:
        grades = sys.argv[1:]
    else:
        grades = [str(i) for i in range(1, 13)]

    # Validate
    for g in grades:
        if g not in ALL_GRADES:
            print(f"Unknown grade: {g}. Valid: {', '.join(ALL_GRADES)}")
            sys.exit(1)

    print(f"Grades to crawl: {', '.join(grades)}")
    driver = create_driver()

    login(driver)
    navigate_to_lp(driver)

    summary = []

    for grade in grades:
        print(f"\n{'='*60}")
        print(f"  Grade: {grade}")
        print(f"{'='*60}")

        if not select_grade(driver, grade):
            print(f"  FAILED to select grade {grade}. Skipping.")
            summary.append((grade, 0, "FAILED"))
            continue

        if not open_skill_details(driver):
            print(f"  FAILED to open Skill Details for grade {grade}. Skipping.")
            summary.append((grade, 0, "NO DETAILS"))
            continue

        go_to_first_skill(driver)
        results = crawl_grade(driver, grade)

        # Save
        out_dir = BASE_DIR / grade_dir_name(grade)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "_crawl_full.json"
        out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Saved {len(results)} skills -> {out_file}")
        summary.append((grade, len(results), "OK"))

        # Close detail view to return to skill list for next grade
        close_detail_view(driver)

    # Print summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"{'Grade':>6s}  {'Skills':>6s}  Status")
    print("-" * 30)
    for grade, count, status in summary:
        print(f"{grade:>6s}  {count:>6d}  {status}")
    total = sum(c for _, c, _ in summary)
    print(f"{'TOTAL':>6s}  {total:>6d}")


if __name__ == "__main__":
    main()
