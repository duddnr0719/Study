README.md
🤖 Smart Scholar Agent: AI-Powered Research & News Archiver
An automated pipeline that crawls latest research papers (Arxiv) and tech news, summarizes them using AI, and archives them into a structured Notion database. This project is designed to help developers and researchers stay updated with the fast-paced AI and Computer Architecture trends without manual effort.

🌟 Key Features
Automated Content Discovery: Periodically crawls specified sources like Arxiv or Tech News outlets using Python.

Intelligent Summarization: Leverages LLMs to extract core insights, methodologies, and 3-line summaries from lengthy articles/papers.

Notion Integration: Seamlessly pushes curated data (Title, Summary, Tags, URL, Date) to a pre-defined Notion database via Notion API.

Customizable Topics: Easily configure keywords such as "Computer Architecture", "LLM", or "Backend Engineering" to filter content.

Agent-Centric Development: Developed in collaboration with AI agents (e.g., OpenCode) to optimize boilerplate code and API handling.

🛠 Tech Stack
Language: Python 3.x

Libraries: BeautifulSoup4, Requests (Crawling), OpenAI / LangChain (AI Summarization), Notion-client (API SDK).

Infrastructure: GitHub Actions (for scheduled automation).

Storage: Notion Workspace (as a personal knowledge base).

🏗 System Architecture
Ingestion: Python script fetches metadata from Arxiv/News RSS feeds based on keywords.

Processing: AI Agent parses the content and generates a concise summary.

Archiving: The formatted data is mapped to Notion Database properties and uploaded via API.

📝 Notion Database Structure
The project expects a Notion database with the following properties:

Name (Title)

Summary (Text)

Tags (Multi-select: AI, Architecture, News, etc.)

Source URL (URL)

Published Date (Date)

🚀 How to Use (Instructions for OpenCode)
"Hey OpenCode, let's build this project step-by-step based on this README. Please start by generating the Python environment setup and the basic Notion API connection script."

Clone this repository.

Set up environment variables in .env:

NOTION_TOKEN: your_notion_api_token_here

NOTION_DATABASE_ID: https://www.notion.so/3009d2cf1d1480788f7ccefd7f4dbc11?v=3009d2cf1d14800d8c59000c452723fb&source=copy_link

USE_ANTIGRAVITY=true

MODEL_NAME=gemini-2.5-flash

Install dependencies: pip install -r requirements.txt.

Run the main script: python main.py.

📈 Future Roadmap
[ ] Add a simple HTML/CSS dashboard for monitoring logs.

[ ] Support PDF parsing for deep-dive paper analysis.

[ ] Integrate Slack/Discord notifications for high-priority updates.
