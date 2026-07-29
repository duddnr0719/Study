# 규정 PDF 준비

이 폴더의 PDF는 **FIA가 저작권을 가진 공식 규정집**이라 저장소에 커밋하지 않는다
(`.gitignore` 처리). `ingest.py`를 돌리기 전에 아래에서 직접 내려받아 이 폴더에 두면 된다.

## 받는 곳

FIA 공식 규정 페이지 — https://www.fia.com/regulation/category/110
(문서 아카이브: https://www.fia.com/documents/category/110-formula-1)

## 필요한 파일명

`ingest.py`의 `PDF_METADATA`가 **파일명으로** 연도·섹션을 판별하므로 이름을 그대로 맞춰야 한다.

| 파일명 | 내용 |
|---|---|
| `f1_regulations_2024.pdf` | 2024 통합 규정집 |
| `f1_2026_section_a_general.pdf` | 2026 Section A — 일반 규정 |
| `f1_2026_section_b_sporting.pdf` | 2026 Section B — 스포팅 규정 |
| `f1_2026_section_c_technical.pdf` | 2026 Section C — 기술 규정 |
| `f1_2026_section_d_financial_teams.pdf` | 2026 Section D — 재정 규정 (팀) |
| `f1_2026_section_e_financial_pu.pdf` | 2026 Section E — 재정 규정 (파워유닛) |
| `f1_2026_section_f_operational.pdf` | 2026 Section F — 운영 규정 |

여기 없는 파일명으로 두면 `PDF_METADATA` 조회에서 빠져 메타데이터 없이 임베딩된다.
7개를 다 받을 필요는 없고, 폴더에 있는 것만 인덱싱된다.

## 이후 절차

```bash
cd f1-project
pip install -r requirements.txt
cp .env.example .env          # GOOGLE_API_KEY 등 채우기
python ingest.py              # PDF → ChromaDB 임베딩
```
