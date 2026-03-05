F1-Expert RAG Agent (F1 Doctor) 🏎️🤖
An intelligent, Retrieval-Augmented Generation (RAG) based assistant designed to provide expert-level insights into Formula 1 regulations and historical race data.

By combining the FIA Technical and Sporting Regulations with historical race statistics via the Ergast API, the F1 Doctor offers precise, evidence-based answers to complex motorsport queries.

🌟 Key Features
Intelligent Regulation Retrieval: Ingests and processes hundreds of pages of official FIA PDF rulebooks. Answers natural language questions with precise citations (e.g., specific article numbers).

Historical Context & Q&A: Synchronizes with the Ergast Developer API to analyze past race incidents. (e.g., "Was the final lap overtake in Abu Dhabi 2021 compliant with safety car regulations?")

Context-Aware Multi-turn Dialogue: Maintains conversation history for seamless follow-up questions regarding penalties, strategies, and technical violations.

🛠️ Tech Stack
AI Models: GPT-4o or Claude 3.5 Sonnet (for generation)

AI Orchestration: LangChain or LlamaIndex

Vector Database: ChromaDB or Pinecone (for storing embedded regulation data)

Backend: FastAPI (Python) - chosen for its asynchronous capabilities and seamless AI model integration

Data Sources: * FIA Official Regulations (PDFs)

Ergast Developer API (Historical race data)

Development Tools:

Claude Code: Used for rapid code implementation and structural generation.

Gemini CLI: Used for model interaction, fine-tuning workflows, and prompt testing.

⚙️ System Architecture & Data Flow
The system operates on a 5-step RAG pipeline:

Data Ingestion (Batch Process): Extract text from FIA PDF rulebooks → Split into logical chunks → Process through an embedding model → Store in the Vector DB.

User Request: The user submits a query (e.g., "What are the overtaking rules under a Safety Car?").

Retrieval: The system queries the Vector DB to find the most semantically relevant regulation articles.

Augmentation: The retrieved regulation texts, the user's original question, and real-time historical data from the Ergast API are combined into a single, enriched prompt.

Generation: The LLM processes the augmented prompt to generate a comprehensive, accurate answer, which is then returned to the user via the FastAPI backend.

🚀 Development Workflow
This project leverages cutting-edge CLI tools to accelerate development:

Implementation: The core backend architecture, API routing, and RAG pipeline are generated and refined using Claude Code.

Model Tuning & Testing: Prompt engineering, model evaluation, and potential fine-tuning tasks are managed directly from the terminal using the Gemini CLI.

💻 Getting Started
Prerequisites

Python 3.10+

Claude Code configured

Gemini CLI installed and authenticated

API Keys (OpenAI/Anthropic, Pinecone/ChromaDB depending on final selection)