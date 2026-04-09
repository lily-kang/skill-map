"""Crawl Pre-K grade skill data from Renaissance Learning Progression site.

Attaches to Chrome on port 9222, logs in, navigates to LP, selects Pre-K,
opens the first skill, and iterates through all skills saving to _crawl_full.json.

Usage:
  1) Start Chrome: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  2) python crawl_prek_full.py
"""

import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

EDUCATOR_ENTRY = "https://global-zone60.renaissance-go.com/educatorportal/entry?t=rpna32xu"
LP_URL = "https://zone60-educator.renaissance-go.com/record-book/star/skill-recommendations/browselearningprogression"
USERNAME = "polyar"
PASSWORD = "sodium7965@"
OUTPUT_DIR = Path(__file__).parent / "Learning_Progression" / "Pre-K"
SCREENSHOT_DIR = Path(__file__).parent

JS_HAS_RECORD_BOOK = '''
    const h = document.querySelector("record-book");
    return !!(h && h.shadowRoot);
'''

JS_EXTRACT = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return null;
    const rb = host.shadowRoot;
    const infoList = rb.querySelector(".single-skill-view.info-list, .info-list");
    if (!infoList) return null;

    // Full description: the div sibling BEFORE info-list
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

    // Extract fields from info-list
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

    const nextLinks = rb.querySelectorAll("a.skill-nav-option");
    let hasNext = false;
    for (const l of nextLinks) {
        if (l.textContent.includes("Next") && !l.classList.contains("disabled")) hasNext = true;
    }

    return { fullDesc, fields, isFocus, hasNext };
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

# JS to click the Pre-K grade tab (inside shadow DOM)
JS_SELECT_PREK = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return "no-record-book";
    const rb = host.shadowRoot;
    // Grade buttons are inside shadow DOM: button.ren-btn
    const btns = rb.querySelectorAll("button.ren-btn");
    for (const b of btns) {
        if (b.textContent.trim() === "Pre-K") {
            b.click();
            return "clicked";
        }
    }
    return "not-found";
'''

# JS to click the first "Skill Details" link to open detail view
JS_CLICK_FIRST_SKILL = '''
    const host = document.querySelector("record-book");
    if (!host || !host.shadowRoot) return "no-record-book";
    const rb = host.shadowRoot;
    // "Skill Details" is a span.ren-link inside the skill list
    const spans = rb.querySelectorAll("span.ren-link");
    for (const s of spans) {
        if (s.textContent.trim() === "Skill Details") {
            s.click();
            return "clicked-skill-details";
        }
    }
    return "not-found";
'''


def ss(driver, name):
    driver.save_screenshot(str(SCREENSHOT_DIR / f"screenshot_{name}.png"))
    print(f"  [{name}] URL: {driver.current_url}")


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

    print("1. Navigating to educator portal...")
    driver.get(EDUCATOR_ENTRY)
    time.sleep(5)
    ss(driver, "1_entry")

    # Check if already logged in (no login form)
    login_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
    if not login_fields:
        print("  Already logged in, skipping login.")
        return

    print("2. Entering credentials...")
    username_input = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='text'], input[name='username'], input[name='userName'], #username, #userName")
    ))
    username_input.clear()
    username_input.send_keys(USERNAME)

    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.clear()
    password_input.send_keys(PASSWORD)

    print("3. Submitting login...")
    submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    submit.click()

    time.sleep(10)
    ss(driver, "3_logged_in")
    print(f"  Logged in: {driver.current_url}")


def navigate_to_lp(driver):
    print("4. Navigating to LP page...")
    driver.get(LP_URL)
    time.sleep(10)

    print("  Waiting for record-book shadow root...")
    if not wait_for_record_book(driver, timeout_sec=120):
        ss(driver, "4_no_record_book")
        raise SystemExit("record-book not found after navigating to LP. Check screenshot.")
    ss(driver, "4_lp_loaded")
    print("  LP page loaded.")


def select_prek(driver):
    print("5. Selecting Pre-K...")
    time.sleep(3)
    result = driver.execute_script(JS_SELECT_PREK)
    print(f"  Select Pre-K result: {result}")
    time.sleep(5)
    ss(driver, "5_prek_selected")
    return result.startswith("clicked")


def open_first_skill(driver):
    print("6. Opening first skill (Skill Details)...")
    time.sleep(3)
    result = driver.execute_script(JS_CLICK_FIRST_SKILL)
    print(f"  Click result: {result}")
    time.sleep(5)
    # Wait for the detail view to load (info-list should appear)
    for _ in range(10):
        has_info = driver.execute_script('''
            const host = document.querySelector("record-book");
            if (!host || !host.shadowRoot) return false;
            const rb = host.shadowRoot;
            return !!(rb.querySelector(".info-list") || rb.querySelector(".single-skill-view"));
        ''')
        if has_info:
            print("  Skill detail view loaded.")
            break
        time.sleep(2)
    ss(driver, "6_first_skill")
    return result != "not-found"


def go_to_first_skill(driver):
    """Navigate back to the very first skill using Prev buttons."""
    print("  Navigating to first skill...")
    while True:
        has_prev = driver.execute_script(JS_PREV)
        if not has_prev:
            break
        time.sleep(0.5)
    print("  At first skill.")
    time.sleep(2)


def crawl_all_skills(driver):
    results = []
    count = 0

    while True:
        time.sleep(1.5)
        data = driver.execute_script(JS_EXTRACT)
        if not data:
            print(f"  Could not extract skill {count+1}. Retrying...")
            time.sleep(3)
            data = driver.execute_script(JS_EXTRACT)
            if not data:
                print("  Still failed. Stopping.")
                break

        fields = data["fields"]
        standard = fields.get("Standards", "")
        skill_code = standard.split(" - ")[0].strip() if " - " in standard else f"UNK_{count}"
        short_name = fields.get("Short Skill Name", "")
        full_desc = data["fullDesc"]

        tag = "FS" if data["isFocus"] else "  "
        print(f"[{count+1:3d}] {tag} {skill_code:25s} | {short_name[:35]:35s} | {full_desc[:50]}")

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
            print(f"\nDone. Total: {count}")
            break
        time.sleep(0.5)

    return results


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    driver = create_driver()

    try:
        login(driver)
        navigate_to_lp(driver)

        if not select_prek(driver):
            raise SystemExit("Could not select Pre-K. Check screenshot_5_prek_selected.png")

        if not open_first_skill(driver):
            raise SystemExit("Could not open first skill. Check screenshot_6_first_skill.png")

        go_to_first_skill(driver)

        results = crawl_all_skills(driver)

        out = OUTPUT_DIR / "_crawl_full.json"
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved {len(results)} skills to {out}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        ss(driver, "error")


if __name__ == "__main__":
    main()
