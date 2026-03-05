import time
from typing import Dict, List

import config


class PaperSummarizer:

    def __init__(self):
        self.use_ai = config.USE_ANTIGRAVITY
        self.client = None

        if self.use_ai:
            try:
                import ollama
                self.client = ollama.Client(host=config.OLLAMA_HOST)
                self.client.list()
                print(f"✅ AI Summarizer initialized (Ollama - Model: {config.MODEL_NAME})")
            except ImportError:
                print("⚠️ ollama 패키지가 설치되지 않았습니다: pip3 install ollama")
                print("   Falling back to rule-based summarization.")
                self.use_ai = False
            except Exception as e:
                print(f"⚠️ Ollama 연결 실패: {e}")
                print("   Ollama가 실행 중인지 확인하세요: ollama serve")
                print("   Falling back to rule-based summarization.")
                self.use_ai = False
        else:
            print("✅ Summarizer initialized (Rule-based mode)")

    def summarize(self, title: str, abstract: str, keyword: str = "") -> str:
        if self.use_ai and self.client:
            try:
                return self._ai_summarize(title, abstract, keyword)
            except Exception as e:
                print(f"⚠️ AI summarization failed: {e}. Using fallback.")
                return self._rule_based_summarize(title, abstract, keyword)
        return self._rule_based_summarize(title, abstract, keyword)

    def _ai_summarize(self, title: str, abstract: str, keyword: str) -> str:
        prompt = (
            f"You are a research paper summarizer. "
            f"Summarize the following research paper in exactly 3 concise sentences:\n"
            f"- Sentence 1: The problem or research question.\n"
            f"- Sentence 2: The proposed method or approach.\n"
            f"- Sentence 3: The key results or contributions.\n\n"
            f"Title: {title}\n"
            f"Abstract: {abstract}\n"
            f"Field: {keyword}\n\n"
            f"Provide only the 3-sentence summary, nothing else."
        )

        response = self.client.chat(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response["message"]["content"].strip()

        if len(summary) > 2000:
            summary = summary[:2000]

        return summary

    def detailed_analyze(self, title: str, abstract: str, keyword: str = "") -> Dict:
        if self.use_ai and self.client:
            try:
                return self._ai_detailed_analyze(title, abstract, keyword)
            except Exception as e:
                print(f"⚠️ AI detailed analysis failed: {e}. Using fallback.")
                return self._rule_based_detailed_analyze(title, abstract, keyword)
        return self._rule_based_detailed_analyze(title, abstract, keyword)

    def _ai_detailed_analyze(self, title: str, abstract: str, keyword: str) -> Dict:
        prompt = (
            f"You are a research paper analyst. Analyze the following paper and provide a detailed breakdown.\n"
            f"Write in Korean. Each section should be 2-4 sentences.\n\n"
            f"Title: {title}\n"
            f"Abstract: {abstract}\n"
            f"Field: {keyword}\n\n"
            f"Respond in EXACTLY this format (keep the section headers as-is):\n"
            f"[연구 배경]\n<background text>\n"
            f"[연구 방법]\n<method text>\n"
            f"[연구 결과]\n<results text>\n"
            f"[연구 결론]\n<conclusion text>"
        )

        response = self.client.chat(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response["message"]["content"].strip()

        sections = {"background": "", "method": "", "results": "", "conclusion": ""}
        current_key = None
        key_map = {
            "[연구 배경]": "background",
            "[연구 방법]": "method",
            "[연구 결과]": "results",
            "[연구 결론]": "conclusion",
        }

        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped in key_map:
                current_key = key_map[stripped]
            elif current_key:
                sections[current_key] += line + "\n"

        for k in sections:
            sections[k] = sections[k].strip()[:2000]

        return sections

    def _rule_based_detailed_analyze(self, title: str, abstract: str, keyword: str) -> Dict:
        sentences = [s.strip() + '.' for s in abstract.split('.') if s.strip()]
        n = len(sentences)
        return {
            "background": sentences[0] if n > 0 else "N/A",
            "method": ' '.join(sentences[1:max(2, n//2)]) if n > 1 else "N/A",
            "results": ' '.join(sentences[max(2, n//2):-1]) if n > 2 else "N/A",
            "conclusion": sentences[-1] if n > 1 else "N/A",
        }

    def _rule_based_summarize(self, title: str, abstract: str, keyword: str) -> str:
        sentences = [s.strip() + '.' for s in abstract.split('.') if s.strip()]

        if not sentences:
            return f"Research paper on {keyword if keyword else 'advanced topics'}."

        problem_statement = sentences[0]

        methodology = ""
        for s in sentences[1:]:
            if any(word in s.lower() for word in [
                'propose', 'present', 'introduce', 'develop',
                'method', 'approach', 'algorithm', 'model', 'framework'
            ]):
                methodology = s
                break
        if not methodology and len(sentences) > 1:
            methodology = sentences[1]

        contribution = ""
        for s in sentences[1:]:
            if any(word in s.lower() for word in [
                'result', 'show', 'demonstrate', 'achieve',
                'improve', 'outperform', 'find', 'conclude'
            ]):
                contribution = s
                break
        if not contribution and len(sentences) > 2:
            contribution = sentences[2]
        elif not contribution and len(sentences) > 1:
            contribution = sentences[-1]

        summary_parts = [problem_statement]
        if methodology:
            summary_parts.append(methodology)
        if contribution:
            summary_parts.append(contribution)

        return ' '.join(summary_parts)

    def batch_summarize(self, papers: List[Dict]) -> List[Dict]:
        summarized_papers = []
        mode = f"Ollama ({config.MODEL_NAME})" if self.use_ai else "Rule-based"

        print(f"\n{'='*80}")
        print(f"🤖 BATCH SUMMARIZATION ({mode} Mode)")
        print(f"{'='*80}")
        print(f"Processing {len(papers)} papers...\n")

        for i, paper in enumerate(papers, 1):
            print(f"[{i}/{len(papers)}] Summarizing: {paper.get('title', 'Untitled')[:60]}...")

            try:
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                keyword = paper.get("keyword", "")

                summary = self.summarize(title, abstract, keyword)
                detailed = self.detailed_analyze(title, abstract, keyword)

                paper["summary"] = summary
                paper["detailed_analysis"] = detailed
                summarized_papers.append(paper)
                print(f"  ✅ Done")

            except Exception as e:
                print(f"  ⚠️ Skipping paper due to error: {str(e)}")
                continue

        print(f"\n✅ Batch summarization completed: {len(summarized_papers)}/{len(papers)} papers")
        print(f"{'='*80}\n")

        return summarized_papers


def main():
    test_paper = {
        "title": "Attention Is All You Need",
        "abstract": (
            "The dominant sequence transduction models are based on complex recurrent "
            "or convolutional neural networks that include an encoder and a decoder. "
            "The best performing models also connect the encoder and decoder through "
            "an attention mechanism. We propose a new simple network architecture, "
            "the Transformer, based solely on attention mechanisms, dispensing with "
            "recurrence and convolutions entirely."
        ),
        "keyword": "Machine Learning"
    }

    summarizer = PaperSummarizer()
    summary = summarizer.summarize(
        title=test_paper["title"],
        abstract=test_paper["abstract"],
        keyword=test_paper["keyword"]
    )

    print("\n" + "="*80)
    print("Test Summary:")
    print("="*80)
    print(summary)


if __name__ == "__main__":
    main()
