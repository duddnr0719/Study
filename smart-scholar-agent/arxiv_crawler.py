import feedparser
import requests
from typing import List, Dict, Optional
from datetime import datetime
import time


class ArxivCrawler:
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self, keywords: List[str], max_results: int = 10):
        self.keywords = keywords
        self.max_results = max_results
        print(f"🔍 Arxiv Crawler initialized with keywords: {', '.join(keywords)}")
    
    def search(self) -> List[Dict]:
        all_results = []
        
        for keyword in self.keywords:
            print(f"\n🔎 Searching Arxiv for: {keyword}")
            
            query = self._build_query(keyword)
            params = {
                "search_query": query,
                "start": 0,
                "max_results": self.max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                
                papers = self._parse_feed(feed, keyword)
                all_results.extend(papers)
                
                print(f"✅ Found {len(papers)} papers for '{keyword}'")
                
                time.sleep(3)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching from Arxiv for '{keyword}': {str(e)}")
                continue
        
        seen_urls = set()
        unique_results = []
        for paper in all_results:
            url = paper.get("source_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(paper)

        duplicates = len(all_results) - len(unique_results)
        print(f"\n📚 Total papers found: {len(all_results)} (중복 {duplicates}편 제거 → {len(unique_results)}편)")
        return unique_results
    
    def _build_query(self, keyword: str) -> str:
        search_fields = ["ti", "abs"]
        query_parts = [f"{field}:{keyword}" for field in search_fields]
        return f"({' OR '.join(query_parts)})"
    
    def _parse_feed(self, feed: feedparser.FeedParserDict, keyword: str) -> List[Dict]:
        papers = []
        
        for entry in feed.entries:
            try:
                published_date = self._parse_date(entry.get("published", ""))
                
                paper = {
                    "title": entry.get("title", "").replace("\n", " ").strip(),
                    "abstract": entry.get("summary", "").replace("\n", " ").strip(),
                    "source_url": entry.get("link", ""),
                    "published_date": published_date,
                    "authors": [author.get("name", "") for author in entry.get("authors", [])],
                    "keyword": keyword,
                    "categories": [tag.get("term", "") for tag in entry.get("tags", [])]
                }
                
                papers.append(paper)
                
            except Exception as e:
                print(f"⚠️ Error parsing entry: {str(e)}")
                continue
        
        return papers
    
    def _parse_date(self, date_string: str) -> Optional[str]:
        try:
            dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%Y-%m-%d")
        except:
            try:
                dt = datetime.strptime(date_string[:10], "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d")
            except:
                return None


def main():
    keywords = ["Large Language Model", "Computer Architecture", "Machine Learning"]
    crawler = ArxivCrawler(keywords=keywords, max_results=5)
    
    papers = crawler.search()
    
    print("\n" + "="*80)
    print("Sample Results:")
    print("="*80)
    
    for i, paper in enumerate(papers[:3], 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   📅 {paper['published_date']}")
        print(f"   🔗 {paper['source_url']}")
        print(f"   📝 {paper['abstract'][:150]}...")


if __name__ == "__main__":
    main()
