#!/usr/bin/env python3

import sys
from typing import List, Dict
from arxiv_crawler import ArxivCrawler
from summarizer import PaperSummarizer
from notion_archiver import NotionArchiver
import config


def prepare_notion_entries(papers: List[Dict]) -> List[Dict]:
    entries = []
    
    for paper in papers:
        keyword = paper.get("keyword", "")
        tags = config.DEFAULT_TAGS.get(keyword, [keyword]) if keyword else ["Research"]
        
        entry = {
            "title": paper.get("title", "Untitled"),
            "summary": paper.get("summary", paper.get("abstract", "")[:500]),
            "tags": tags,
            "source_url": paper.get("source_url", ""),
            "published_date": paper.get("published_date"),
            "detailed_analysis": paper.get("detailed_analysis")
        }
        entries.append(entry)
    
    return entries


def main():
    print("="*80)
    print("🤖 Smart Scholar Agent: AI-Powered Research Archiver")
    print("="*80)
    
    try:
        print("\n📋 Step 1: Initializing Components...")
        crawler = ArxivCrawler(
            keywords=config.SEARCH_KEYWORDS,
            max_results=config.MAX_RESULTS_PER_KEYWORD
        )
        summarizer = PaperSummarizer()
        archiver = NotionArchiver()
        
        if not archiver.test_connection():
            print("❌ Failed to connect to Notion. Please check your credentials.")
            return 1
        
        print("\n📚 Step 2: Crawling Arxiv for Research Papers...")
        papers = crawler.search()
        
        if not papers:
            print("⚠️ No papers found. Exiting.")
            return 0
        
        print(f"\n🤖 Step 3: Generating AI Summaries for {len(papers)} papers...")
        summarized_papers = summarizer.batch_summarize(papers)
        
        if not summarized_papers:
            print("⚠️ No papers successfully summarized. Exiting.")
            return 0
        
        print(f"\n📤 Step 4: Archiving {len(summarized_papers)} papers to Notion...")
        entries = prepare_notion_entries(summarized_papers)
        results = archiver.batch_add_entries(entries)
        
        print("\n" + "="*80)
        print(f"✅ SUCCESS! Archived {len(results)} papers to your Notion database.")
        print("="*80)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user. Exiting gracefully...")
        return 130
    
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
