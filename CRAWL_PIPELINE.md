# Skill Crawling Pipeline

Renaissance Educator Portal에서 학년별 세부 스킬 데이터를 크롤링하는 절차.

---

## 사전 준비

```bash
# Chrome을 remote debugging 모드로 실행
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

Python 의존성: `selenium` (ChromeDriver 필요)

---

## 스크립트 목록

| 스크립트 | 용도 | 입력 | 출력 |
|----------|------|------|------|
| `crawl_prek_full.py` | **Pre-K 전체 자동화** (로그인→LP→Pre-K 선택→Skill Details→전체 순회) | Chrome :9222 | `Learning_Progression/Pre-K/_crawl_full.json` |
| `crawl_k_grade.py` | K 로그인 + LP 페이지 탐색 (반자동) | Chrome :9222 | 스크린샷, page source |
| `crawl_k_skills.py` | K 스킬 순회 (View Skill 패널 열린 상태에서) | Chrome :9222 | `Learning_Progression/K/` HTML 파일들 |
| `crawl_k_descriptions.py` | K 스킬 상세 재크롤링 (full_description 포함) | Chrome :9222 | `Learning_Progression/K/_crawl_full.json` |
| `crawl_prek_descriptions.py` | Pre-K 스킬 순회 (View Skill 패널 열린 상태에서) | Chrome :9222 | `Learning_Progression/Pre-K/_crawl_full.json` |
| `export_prek_crawl_from_html.py` | 기존 HTML에서 오프라인으로 JSON 생성 (Selenium 불필요) | HTML 파일들 | `_crawl_full.json` |
| `verify_skill_counts.py` | **학년별 스킬 수 검증** (LP 페이지 vs skills.json) | Chrome :9222 | 터미널 출력 |
| `parse_skills.py` | HTML → 구조화된 `skills.json` 변환 | `_crawl_full.json` 또는 HTML | `skills.json` |

---

## 크롤링 흐름 (Pre-K 예시)

```
1. Chrome :9222 실행
2. python crawl_prek_full.py
   ├── 로그인 (EDUCATOR_ENTRY → username/password 입력)
   ├── LP 페이지 이동 (LP_URL)
   ├── Shadow DOM 내 Pre-K 버튼 클릭 (button.ren-btn)
   ├── "Skill Details" 링크 클릭 → 상세 뷰 진입
   ├── Prev 반복 → 첫 번째 스킬로 이동
   └── Next 반복하며 전체 스킬 추출
       ├── JS_EXTRACT: info-list에서 필드 파싱
       └── 결과를 _crawl_full.json에 저장
3. python parse_skills.py  ← skills.json 재생성
```

---

## 다른 학년 크롤링 시

`crawl_prek_full.py`를 복사하여 수정:

1. `OUTPUT_DIR` 경로를 해당 학년으로 변경 (e.g. `Learning_Progression/1/`)
2. `JS_SELECT_PREK`에서 클릭 대상 텍스트 변경 (e.g. `"Pre-K"` → `"1"`)
3. 실행: `python crawl_grade_X.py`

---

## 핵심 기술 노트

- Renaissance LP 페이지는 `<record-book>` Web Component 안에 **Shadow DOM**을 사용함
- 모든 DOM 접근은 `document.querySelector("record-book").shadowRoot`를 통해야 함
- 스킬 네비게이션: `a.skill-nav-option` (Prev Skill / Next Skill)
- 상세 뷰 진입: `span.ren-link` "Skill Details" 클릭
- 추출 대상 필드: Short Skill Name, Skill Area, Domains, Standards, Prerequisite Skills, ELL Support, Content-Area Vocabulary, Conceptual Knowledge, Linguistic Competencies, Domain Level Expectations

---

## 출력 형식 (`_crawl_full.json`)

```json
[
  {
    "skill_code": "CP.R.PK.FO.FR.1",
    "skill_name": "Read and share meaning of environmental signs",
    "full_description": "Read and tell the meaning of familiar signs and symbols...",
    "standard": "CP.R.PK.FO.FR.1 - Features of print",
    "is_focus": true,
    "fields": {
      "Short Skill Name": "...",
      "Skill Area": "Print Concepts",
      "Domains": "Foundations for Reading",
      "Standards": "CP.R.PK.FO.FR.1 - Features of print",
      "Prerequisite Skills": "...",
      "ELL Support": "...",
      "Conceptual Knowledge": "...",
      "Content-Area Vocabulary": "...",
      "Linguistic Competencies": "...",
      "Domain Level Expectations": "..."
    }
  }
]
```
