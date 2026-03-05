import os
from typing import Dict, List, Optional
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()


class NotionArchiver:
    
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        
        if not self.token:
            raise ValueError("NOTION_TOKEN not found in environment variables")
        if not self.database_id:
            raise ValueError("NOTION_DATABASE_ID not found in environment variables")
        
        self.client = Client(auth=self.token)
        print(f"✅ Notion client initialized successfully")
    
    def test_connection(self) -> bool:
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            print(f"✅ Successfully connected to database: {database.get('title', [{}])[0].get('plain_text', 'Untitled')}")
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return False
    
    def _build_detail_blocks(self, detailed_analysis: Dict) -> List[Dict]:
        sections = [
            ("연구 배경", detailed_analysis.get("background", "")),
            ("연구 방법", detailed_analysis.get("method", "")),
            ("연구 결과", detailed_analysis.get("results", "")),
            ("연구 결론", detailed_analysis.get("conclusion", "")),
        ]
        blocks = [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": "📋 논문 상세 분석"}}]
                }
            },
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            },
        ]
        for heading, content in sections:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": heading}}]
                }
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content if content else "N/A"}}]
                }
            })
        return blocks

    def add_entry(
        self,
        title: str,
        summary: str,
        tags: List[str],
        source_url: str,
        published_date: Optional[str] = None,
        detailed_analysis: Optional[Dict] = None
    ) -> Dict:
        try:
            date_value = None
            if published_date:
                try:
                    if isinstance(published_date, str):
                        date_value = {"start": published_date}
                except Exception as e:
                    print(f"⚠️ Date parsing error: {e}. Skipping date.")

            properties = {
                "이름": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": summary[:2000]
                            }
                        }
                    ]
                },
                "Tags": {
                    "multi_select": [{"name": tag} for tag in tags]
                },
                "Source URL": {
                    "url": source_url
                }
            }

            if date_value:
                properties["Published Date"] = {"date": date_value}

            children = []
            if detailed_analysis:
                children = self._build_detail_blocks(detailed_analysis)

            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )

            print(f"✅ Added to Notion: {title}")
            return response
        
        except Exception as e:
            print(f"❌ Failed to add entry '{title}': {str(e)}")
            raise
    
    def get_existing_urls(self) -> set:
        urls = set()
        try:
            has_more = True
            start_cursor = None
            while has_more:
                kwargs = {"database_id": self.database_id, "page_size": 100}
                if start_cursor:
                    kwargs["start_cursor"] = start_cursor
                response = self.client.databases.query(**kwargs)
                for page in response.get("results", []):
                    url_prop = page.get("properties", {}).get("Source URL", {})
                    url = url_prop.get("url")
                    if url:
                        urls.add(url)
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            print(f"📋 Notion DB에 기존 논문 {len(urls)}편 확인")
        except Exception as e:
            print(f"⚠️ 기존 데이터 조회 실패: {e}")
        return urls

    def batch_add_entries(self, entries: List[Dict]) -> List[Dict]:
        existing_urls = self.get_existing_urls()

        results = []
        skipped = 0
        for entry in entries:
            source_url = entry.get("source_url", "")
            if source_url in existing_urls:
                skipped += 1
                print(f"⏭️ 이미 존재 (스킵): {entry.get('title', 'Untitled')[:60]}")
                continue
            try:
                response = self.add_entry(
                    title=entry.get("title", "Untitled"),
                    summary=entry.get("summary", ""),
                    tags=entry.get("tags", []),
                    source_url=entry.get("source_url", ""),
                    published_date=entry.get("published_date"),
                    detailed_analysis=entry.get("detailed_analysis")
                )
                results.append(response)
            except Exception as e:
                print(f"⚠️ Skipping entry due to error: {str(e)}")
                continue

        print(f"✅ Batch completed: {len(results)}편 추가 / {skipped}편 중복 스킵 (전체 {len(entries)}편)")
        return results


def main():
    try:
        archiver = NotionArchiver()
        
        if archiver.test_connection():
            print("\n🎉 Notion API setup complete!")
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")


if __name__ == "__main__":
    main()
