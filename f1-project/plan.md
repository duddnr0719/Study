# Architecture Migration Plan: F1-Expert RAG Agent (F1 Doctor)

## 1. Migration Objective
You are tasked with refactoring the existing backend architecture of the "F1 Doctor" AI agent. The goal is to upgrade the Web Search pipeline for better RAG performance and replace the public live timing API with a proprietary F1 TV Premium integration for both telemetry and real-time team radio transcription.

## 2. Target API & Tech Stack State
Please update the current system to match the following architecture:

| Component | Target Service / Tool | Authentication | Cost / Execution Context |
| :--- | :--- | :--- | :--- |
| **LLM** | Ollama `qwen3.5:122b` | None | Free (Remote Server via Tailscale) |
| **Embedding** | Google Gemini `gemini-embedding-001` | `GOOGLE_API_KEY` | Free Tier (Handled by FastAPI Backend) |
| **Historical Data** | Jolpica F1 API | None | Free |
| **Live Telemetry & Audio** | F1 TV Premium | F1 TV Account Credentials | Active Subscription (Replaces OpenF1 API) |
| **Local STT (Audio)** | Faster-Whisper | None | Local Edge Execution (Utilizing local 12GB VRAM) |
| **Web Search**| Tavily API + DuckDuckGo | `TAVILY_API_KEY` | Free Tier + Free Fallback |

## 3. Implementation Steps for Claude Code

Execute the refactoring in the following order. Test each step before moving to the next.

### Step 1: Web Search Engine Refactoring (Fallback Routing)
* **Goal:** Improve search quality for RAG while maintaining system stability.
* **Task:** Implement a custom LangChain search tool.
* **Logic:** The tool must attempt to use the **Tavily Search API** first. Wrap this in a `try/except` block. If Tavily throws a rate-limit error or any other exception, automatically fall back to using the **DuckDuckGo Search** tool. Return the results seamlessly to the agent.

### Step 2: F1 TV Premium Integration (Live Telemetry)
* **Goal:** Replace `OpenF1 API` with direct F1 TV Premium data.
* **Task:** Implement an authentication module using F1 TV Premium credentials to retrieve session tokens.
* **Logic:** Use the token to connect to the F1 TV SignalR/WebSocket endpoints. Stream live telemetry data (speed, throttle, brake) and race control messages, storing them in an in-memory state or Redis cache for the LLM to access.

### Step 3: Local Team Radio Transcription Pipeline (Audio-to-Text)
* **Goal:** Extract live driver audio and transcribe it locally.
* **Task:** Write a Python script using `streamlink` or `FFmpeg` to pull the onboard audio stream from the F1 TV Premium feed.
* **Logic:** Route this audio stream into a **Faster-Whisper** model running locally. Ensure the Whisper model is configured to utilize the local 12GB VRAM GPU efficiently. Send the transcribed text output directly to the LangChain memory context.

### Step 4: Agent Orchestration Update
* **Goal:** Connect the new pipelines to the LLM.
* **Task:** Update the main `/chat` endpoint.
* **Logic:** Ensure the LLM (running remotely via Tailscale) can successfully ingest the Gemini-embedded static regulations, the historical Jolpica data, the new Web Search fallback tool, the live telemetry state, and the real-time transcribed team radio text to formulate its final response.