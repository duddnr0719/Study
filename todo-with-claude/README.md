# Smart AI-Driven Task Management System (Backend)

A smart To-Do backend service that leverages LLMs to analyze user intent, extract schedules, and prioritize tasks based on natural language input.

## 🚀 Project Overview
The goal of this project is to build a high-performance backend that goes beyond simple CRUD operations. It uses AI to:
- Parse natural language into structured data (dates, priority, categories).
- Recommend optimal task ordering based on user patterns and deadlines.
- Seamlessly synchronize with Notion for centralized documentation.

## 🛠 Tech Stack
- **Language/Framework:** Python 3.10+ / FastAPI
- **Database:** PostgreSQL (SQLAlchemy ORM)
- **AI Integration:** Claude API (via LangChain or Anthropic SDK)
- **Development Tool:** Claude Code CLI (for autonomous coding & refactoring)
- **External Integration:** Notion API (for sync and logging)
- **Deployment (Planned):** Dockerized environment on Linux/macOS

## 🤖 Claude Code Instructions (Project Context)
This repository is designed to be managed and developed with **Claude Code CLI**. When performing tasks, please adhere to the following:
1. **API First:** Ensure all endpoints follow RESTful conventions.
2. **Context Awareness:** When generating code, consider the existing database schema and Pydantic models.
3. **AI Logic:** Focus on the `services/ai_engine.py` to refine prompt engineering for intent extraction.
4. **Test-Driven:** Generate unit tests for every new feature using `pytest`.

## 📂 Directory Structure (Planned)
```text
.
├── app/
│   ├── api/          # Route handlers
│   ├── core/         # Config and security
│   ├── models/       # Database schemas
│   ├── schemas/      # Pydantic models
│   ├── services/     # AI logic & Notion sync service
│   └── main.py       # Entry point
├── tests/            # Test suites
├── scripts/          # Migration and utility scripts
├── .env              # Environment variables
└── README.md