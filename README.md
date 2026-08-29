# Study
개인 학습 및 사이드 프로젝트 모음

---

## 📁 프로젝트 목록

### 🏎️ f1-project — F1 규정 & 데이터 전문 AI 챗봇 → 독립 레포로 이동
> Python · FastAPI · LangGraph · ChromaDB · Groq LLM

**[duddnr0719/f1-project](https://github.com/duddnr0719/f1-project)로 분리했습니다** (2026-08-30, 이력 보존).
FIA 공식 규정 PDF(2024/2026)와 실시간 F1 레이스 데이터를 결합한 RAG 기반 AI 어시스턴트 — 상세는 새 레포 README 참고.

---

### ☕ f1-manager — F1 드라이버 관리 REST API
> Java · Spring Boot · JPA · H2 · Lombok

F1 드라이버 정보를 등록하고 조회하는 **간단한 CRUD REST API** 서버입니다.

- `GET /drivers` — 전체 드라이버 목록 조회
- `POST /drivers` — 새 드라이버 등록 (이름, 소속 팀, 포인트)
- 앱 시작 시 샘플 데이터 자동 주입 (Verstappen, Hamilton 등)
- Spring Boot + JPA로 빠르게 구성한 백엔드 실습 프로젝트

---

### ☸️ k8s — Kubernetes GPU 워크로드 배포 설정
> Kubernetes · Kustomize · NVIDIA CUDA · Shell Script

NVIDIA GPU가 탑재된 Kubernetes 클러스터에 **GPU 워크로드를 배포하기 위한 YAML 및 스크립트 모음**입니다.

- CUDA 12.3 / Ubuntu 22.04 기반 컨테이너 환경
- GPU 수량(1/2/4/8)별 프리셋 YAML로 간편 배포
- Pod / Deployment / StatefulSet 세 가지 배포 유형 지원
- Kustomize 오버레이로 환경별 설정 관리
- `deploy-gpu-pod.sh` 등 자동화 셸 스크립트 포함
- nodeSelector + taint toleration으로 GPU 노드 타겟팅

---

## 🗂️ 기타 프로젝트
| 폴더 | 설명 |
|------|------|
| `smart-scholar-agent` | arXiv 논문 크롤러 + Notion 자동 아카이빙 |
| `todo-with-claude` | FastAPI + Claude AI 기반 할일 관리 앱 |
