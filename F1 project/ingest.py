import os
import re
import json
import shutil
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

EMBEDDING_MODEL  = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
CHUNK_BATCH_SIZE = 100   # API 1회당 최대 텍스트 수
API_CALL_DELAY   = 65    # 배치 간격 (초) - 무료 티어 분당 100회 제한 대기
RETRY_DELAY      = 25    # 429 에러 시 재시도 대기 (초)
CHECKPOINT_FILE  = "./ingest_checkpoint.json"

# 파일명 → (연도, 섹션 설명) 매핑
PDF_METADATA = {
    # 2024
    "f1_regulations_2024.pdf":               ("2024", "통합 규정집"),
    # 2026 (최신 규정)
    "f1_2026_section_a_general.pdf":         ("2026", "Section A - 일반 규정"),
    "f1_2026_section_b_sporting.pdf":        ("2026", "Section B - 스포팅 규정"),
    "f1_2026_section_c_technical.pdf":       ("2026", "Section C - 기술 규정"),
    "f1_2026_section_d_financial_teams.pdf": ("2026", "Section D - 재정 규정 (팀)"),
    "f1_2026_section_e_financial_pu.pdf":    ("2026", "Section E - 재정 규정 (파워유닛)"),
    "f1_2026_section_f_operational.pdf":     ("2026", "Section F - 운영 규정"),
}


class RateLimitedEmbeddings(GoogleGenerativeAIEmbeddings):
    """API 호출 사이 딜레이 + 429 에러 자동 재시도 임베딩 클래스"""

    def embed_documents(self, texts, **kwargs):
        results = []
        for i in range(0, len(texts), CHUNK_BATCH_SIZE):
            batch = texts[i:i + CHUNK_BATCH_SIZE]
            batch_num = i // CHUNK_BATCH_SIZE + 1
            total = (len(texts) + CHUNK_BATCH_SIZE - 1) // CHUNK_BATCH_SIZE
            print(f"    배치 {batch_num}/{total} ({len(batch)}개 텍스트)...")

            if i > 0:
                print(f"    {API_CALL_DELAY}초 대기 중...")
                time.sleep(API_CALL_DELAY)

            # 429 에러 시 최대 3번 재시도
            for attempt in range(3):
                try:
                    batch_result = super().embed_documents(batch, **kwargs)
                    results.extend(batch_result)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        if attempt < 2:
                            print(f"    ⚠ 429 에러 - {RETRY_DELAY}초 후 재시도 ({attempt+1}/3)...")
                            time.sleep(RETRY_DELAY)
                        else:
                            print(f"    ❌ 쿼터 초과 - 하루 한도에 도달했습니다.")
                            print(f"    → UTC 자정(한국시간 오전 9시) 이후 python ingest.py 를 다시 실행하세요.")
                            raise
                    else:
                        raise
        return results


def load_pdf_with_metadata(file_path: str) -> list:
    """PDF를 로드하고 각 페이지에 연도/섹션 메타데이터를 추가합니다."""
    filename = os.path.basename(file_path)
    season, section = PDF_METADATA.get(filename, ("unknown", filename))

    print(f"[LOAD] {filename} (시즌: {season}, 섹션: {section})")
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    for doc in documents:
        doc.metadata["season"]      = season
        doc.metadata["section"]     = section
        doc.metadata["source_file"] = filename

    print(f"       → {len(documents)}페이지 로드 완료")
    return documents


def save_checkpoint(batch_idx: int):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"last_completed_batch": batch_idx}, f)


def load_checkpoint() -> int:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f).get("last_completed_batch", -1)
    return -1


def run_ingestion(data_dir: str = "./data"):
    pdf_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".pdf")])
    if not pdf_files:
        print("[ERROR] PDF 파일이 없습니다.")
        return

    print(f"\n[START] 총 {len(pdf_files)}개 PDF 처리 시작")
    print("=" * 60)

    # 1. 모든 PDF 로드 및 청크 분할
    all_documents = []
    for pdf in pdf_files:
        docs = load_pdf_with_metadata(os.path.join(data_dir, pdf))
        all_documents.extend(docs)

    print(f"\n[SPLIT] 전체 {len(all_documents)}페이지 → 청크 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    all_chunks = text_splitter.split_documents(all_documents)
    total_chunks = len(all_chunks)
    total_batches = (total_chunks + CHUNK_BATCH_SIZE - 1) // CHUNK_BATCH_SIZE
    print(f"[SPLIT] 총 청크 수: {total_chunks} / 배치 수: {total_batches}")

    # 2. 체크포인트 확인 (이어하기 지원)
    start_batch = load_checkpoint() + 1
    chroma_path = "./chroma_db"

    if start_batch > 0:
        print(f"\n[RESUME] 체크포인트 발견: 배치 {start_batch}부터 재개합니다.")
        # 기존 DB에 추가
        embeddings = RateLimitedEmbeddings(model=EMBEDDING_MODEL)
        vector_db  = Chroma(persist_directory=chroma_path, embedding_function=embeddings)
    else:
        # 새로 시작: 기존 DB 삭제
        if os.path.exists(chroma_path):
            print(f"\n[WARN] 기존 chroma_db 삭제 후 재생성...")
            shutil.rmtree(chroma_path)
        embeddings = RateLimitedEmbeddings(model=EMBEDDING_MODEL)
        vector_db  = Chroma(persist_directory=chroma_path, embedding_function=embeddings)

    estimated = (total_batches - start_batch - 1) * API_CALL_DELAY
    print(f"\n[EMBED] Google Gemini 임베딩 시작 ({EMBEDDING_MODEL})")
    print(f"        남은 배치: {total_batches - start_batch}개 / 예상 소요: 약 {estimated//60}분 {estimated%60}초\n")

    # 3. 배치별 임베딩 + 체크포인트 저장
    for batch_idx in range(start_batch, total_batches):
        start = batch_idx * CHUNK_BATCH_SIZE
        end   = min(start + CHUNK_BATCH_SIZE, total_chunks)
        batch_chunks = all_chunks[start:end]

        print(f"  [배치 {batch_idx+1}/{total_batches}] 청크 {start+1}~{end}...")

        if batch_idx > start_batch:
            print(f"    {API_CALL_DELAY}초 대기 중...")
            time.sleep(API_CALL_DELAY)

        try:
            vector_db.add_documents(batch_chunks)
            save_checkpoint(batch_idx)
            print(f"    ✓ 완료 (체크포인트 저장)")
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"\n⛔ 하루 쿼터 초과! 배치 {batch_idx}에서 중단됨.")
                print(f"   체크포인트: {CHECKPOINT_FILE}")
                print(f"   → UTC 자정(한국시간 오전 9시) 이후 다시 실행하면 여기서 재개됩니다.")
                return
            raise

    # 4. 완료
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"\n[DONE] 임베딩 완료! {chroma_path}에 저장됨")
    print("=" * 60)

    from collections import Counter
    season_counts = Counter(c.metadata.get("season", "?") for c in all_chunks)
    print("\n[요약] 시즌별 청크 수:")
    for season, count in sorted(season_counts.items()):
        print(f"  {season}년: {count}개 청크")


if __name__ == "__main__":
    data_dir = "./data"
    if not os.path.exists(data_dir):
        print("[ERROR] ./data 디렉토리가 없습니다.")
        exit(1)
    run_ingestion(data_dir)
