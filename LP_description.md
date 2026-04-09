# SR Skill Map

## 배경

**Renaissance**는 **Star Reading(SR)** 이라는 리딩 역량 평가 시험을 제공한다. 이 시험은 Pre-K부터 12학년까지의 학생들을 대상으로 하며, 각 학년별로 학생이 습득해야 할 Reading Skill들을 **Learning Progression**이라는 체계로 정의하고 이를 제공하고 있다.

이 프로젝트는 Renaissance의 Learning Progression 데이터를 구조화하고, 스킬 간 연결 관계를 기반으로 한 Knowledge 시스템을 구축하는 것을 목표로 한다.

---

## 데이터 소스

- **출처**: Renaissance Educator Portal (`zone60-educator.renaissance-go.com`)
- **범위**: Pre-K ~ 12학년, 총 **1,034개 스킬**

### 학년별 현황

| 학년 | 전체 | Focus | Non-focus | 비고 |
|------|------|-------|-----------|------|
| Pre-K | 45 | 11 | 34 | |
| K | 88 | 54 | 34 | |
| 1 | 101 | 53 | 48 | |
| 2 | 84 | 40 | 44 | |
| 3 | 71 | 32 | 39 | |
| 4 | 69 | 30 | 39 | |
| 5 | 80 | 29 | 51 | |
| 6 | 71 | 23 | 48 | |
| 7 | 76 | 27 | 49 | |
| 8 | 72 | 19 | 53 | |
| 9 | 73 | 21 | 52 | |
| 10 | 71 | 22 | 49 | |
| 11 | 64 | 21 | 43 | |
| 12 | 69 | 20 | 49 | |
| **합계** | **1,034** | **402** | **632** | |

** 1 standard에 여러 세부 스킬 존재

### 도메인 (9개)

- Comprehension of Elements and Ideas
- Organization, Purpose, and Language Use
- Vocabulary Development
- Analysis, Evaluation, and Extending Meaning
- Structure, Genre, and Author's Craft
- Comprehension of Information and Ideas
- Foundations for Reading
- Extending Meaning and Deepening Understanding
- Other Subject Areas

---

## 데이터 구조

### `skills.json` 공통 필드

| 필드 | 설명 |
|------|------|
| `skill_code` | Standard 코드 (예: `CP.R.3.FO.FR.1`) |
| `skill_name` | 스킬 짧은 이름 |
| `full_description` | 스킬 전체 설명 |
| `grade` | 학년 (`Pre-K`, `K`, `1`~`12`) |
| `is_focus_skill` | Focus Skill 여부 |
| `skill_area` | 스킬 세부 영역 |
| `domain` | 도메인 |
| `domain_level_expectations` | 도메인 수준 기대치 |
| `standard` | Standard 코드 + 이름 |
| `prerequisite_skills` | 선행 스킬 목록 (`[{grade, description}]`) |

### Focus Skill 추가 필드

| 필드 | 설명 |
|------|------|
| `ell_support` | ELL(영어 학습자) 지원 방법 |
| `content_area_vocabulary` | 핵심 어휘 목록 (배열) |
| `conceptual_knowledge` | 개념적 이해 요소 |
| `linguistic_competencies` | 언어적 역량 요소 |

---

## Skill Map 시각화 

`http://192.168.50.84:8507/`에서 인터랙티브 Skill Map을 확인할 수 있다. (유관부서 공유용)

### 기능

**공통 필터 (Graph/List 공통 적용)**
- 학년 필터 (Grade 버튼 멀티 선택)
- 도메인 필터 (체크박스, Focus 비율 바 표시)
- Focus Skills only 토글
- 검색 (스킬명, 코드, 설명)

**Graph 뷰**
- Force-directed 그래프: 학년 허브 노드 중심으로 스킬 배치
- 선행 스킬 연결선 표시/숨기기
- 스킬 클릭 시 체인 하이라이트 (선행 + 후행)

**List 뷰**
- 학년별 아코디언 (클릭으로 접기/펼치기)
- Standard별 그룹핑
- Focus 표시, 도메인 태그, 스킬 코드

**상세 패널 (우측, 드래그로 너비 조정)**
- Skill Code, Full Description, Skill Area, Domain, Standard
- Prerequisite Skills (클릭 시 해당 스킬로 이동 가능)
- Focus Skill: ELL Support, Vocabulary, Conceptual Knowledge, Linguistic Competencies
- Same Standard: 같은 Standard 코드를 공유하는 형제 스킬 목록

---

## 목표

### 1. Knowledge 구축
- Skill 데이터를 단순 저장이 아닌, **Skill 간의 관계까지 포함한 구조화된 Knowledge**로 구축
- 선행 스킬 체인(어떤 스킬을 배우려면 무엇을 먼저 알고 있어야 하는가)이 탐색 가능한 형태여야 함

### 2. AI Agent 연동
- 구축된 Knowledge를 실제 AI 서비스(Agent) 개발에 활용
- 예: 학생의 취약 Skill을 진단하거나, 학습 경로를 추천

### 3. 업무자 시각화
- Knowledge를 관련 유관 업무 담당자들이 **시각적으로 확인하고 탐색**할 수 있어야 함
- Graph 뷰 / List 뷰 제공
