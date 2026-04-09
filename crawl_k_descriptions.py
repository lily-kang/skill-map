"""Re-crawl K grade: get full_description from the sibling div before info-list.
Assumes: Chrome on port 9222, logged in, K grade detail panel open.
"""

import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

JS_EXTRACT = '''
    const rb = document.querySelector("record-book").shadowRoot;
    const infoList = rb.querySelector(".single-skill-view.info-list, .info-list");
    if (!infoList) return null;

    // Full description: the div.single-skill-view sibling BEFORE info-list (after the HR)
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

    const isFocus = fullText.includes("ELL Support") || fullText.includes("Conceptual Knowledge");

    const nextLinks = rb.querySelectorAll("a.skill-nav-option");
    let hasNext = false;
    for (const l of nextLinks) {
        if (l.textContent.includes("Next") && !l.classList.contains("disabled")) hasNext = true;
    }

    return { fullDesc, fields, isFocus, hasNext };
'''

JS_NEXT = '''
    const rb = document.querySelector("record-book").shadowRoot;
    const links = rb.querySelectorAll("a.skill-nav-option");
    for (const l of links) {
        if (l.textContent.includes("Next") && !l.classList.contains("disabled")) {
            l.click(); return true;
        }
    }
    return false;
'''

JS_PREV = '''
    const rb = document.querySelector("record-book").shadowRoot;
    const links = rb.querySelectorAll("a.skill-nav-option");
    for (const l of links) {
        if (l.textContent.includes("Prev") && !l.classList.contains("disabled")) {
            l.click(); return true;
        }
    }
    return false;
'''


def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)

    # Go back to first skill
    print("Navigating to first skill...")
    while True:
        has_prev = driver.execute_script(JS_PREV)
        if not has_prev:
            break
        time.sleep(0.5)
    print("At first skill.")
    time.sleep(2)

    results = []
    count = 0

    while True:
        time.sleep(1.5)
        data = driver.execute_script(JS_EXTRACT)
        if not data:
            print("Could not extract. Stopping.")
            break

        fields = data["fields"]
        standard = fields.get("Standards", "")
        skill_code = standard.split(" - ")[0].strip() if " - " in standard else f"UNK_{count}"
        short_name = fields.get("Short Skill Name", "")
        full_desc = data["fullDesc"]

        tag = "FS" if data["isFocus"] else "  "
        print(f"[{count+1:2d}] {tag} {skill_code:20s} | {short_name[:35]:35s} | {full_desc[:55]}")

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

    out = Path(__file__).parent / "Learning_Progression" / "K" / "_crawl_full.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
