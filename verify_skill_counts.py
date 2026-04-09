"""Verify skill counts: compare skills.json vs Renaissance LP page per grade.

Usage:
  1) Chrome on port 9222, logged in or not (script logs in automatically)
  2) python verify_skill_counts.py
"""

import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from collections import Counter

EDUCATOR_ENTRY = "https://global-zone60.renaissance-go.com/educatorportal/entry?t=rpna32xu"
LP_URL = "https://zone60-educator.renaissance-go.com/record-book/star/skill-recommendations/browselearningprogression"
USERNAME = "polyar"
PASSWORD = "sodium7965@"
SKILLS_JSON = Path(__file__).parent / "skills.json"

GRADES = ["Pre-K", "K"] + [str(i) for i in range(1, 13)]

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

JS_COUNT_SKILLS = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return -1;
    const rb = host.shadowRoot;
    return rb.querySelectorAll(".skill-info-container").length;
'''


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

    login_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    if not login_fields:
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
    print("  Logged in.")


def load_skills_json_counts():
    if not SKILLS_JSON.exists():
        print(f"WARNING: {SKILLS_JSON} not found")
        return {}
    data = json.loads(SKILLS_JSON.read_text(encoding="utf-8"))
    counts = Counter(s["grade"] for s in data)
    return dict(counts)


def main():
    json_counts = load_skills_json_counts()

    driver = create_driver()
    login(driver)

    print("Navigating to LP...")
    driver.get(LP_URL)
    time.sleep(10)
    if not wait_for_record_book(driver, timeout_sec=120):
        raise SystemExit("record-book not found.")

    print()
    print(f"{'Grade':>6s}  {'LP Page':>8s}  {'skills.json':>11s}  {'Match':>5s}")
    print("-" * 40)

    mismatches = []

    for grade in GRADES:
        result = driver.execute_script(JS_SELECT_GRADE, grade)
        if result != "clicked":
            print(f"{grade:>6s}  {'N/A':>8s}  {json_counts.get(grade, '?'):>11}  {'???':>5s}")
            continue

        # Wait for skill list to load
        time.sleep(4)
        # Wait until count stabilizes
        prev_count = -1
        for _ in range(5):
            lp_count = driver.execute_script(JS_COUNT_SKILLS)
            if lp_count == prev_count and lp_count > 0:
                break
            prev_count = lp_count
            time.sleep(2)

        jc = json_counts.get(grade, 0)
        match = "OK" if lp_count == jc else "DIFF"
        if lp_count != jc:
            mismatches.append((grade, lp_count, jc))

        print(f"{grade:>6s}  {lp_count:>8d}  {jc:>11d}  {match:>5s}")

    print("-" * 40)
    if mismatches:
        print(f"\n{len(mismatches)} mismatch(es):")
        for grade, lp, jc in mismatches:
            diff = lp - jc
            print(f"  {grade}: LP has {lp}, skills.json has {jc} ({'+' if diff > 0 else ''}{diff})")
    else:
        print("\nAll grades match!")


if __name__ == "__main__":
    main()
