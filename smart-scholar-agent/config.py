import os
from dotenv import load_dotenv

load_dotenv()

# AI Model Configuration (Ollama local LLM)
USE_ANTIGRAVITY = os.getenv("USE_ANTIGRAVITY", "false").lower() == "true"
MODEL_NAME = os.getenv("MODEL_NAME", "gemma3")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Search Configuration
SEARCH_KEYWORDS = [
    "Large Language Model",
    "Computer Architecture",
    "Machine Learning",
    "Backend Engineering",
    "Distributed Systems"
]

MAX_RESULTS_PER_KEYWORD = 5

DEFAULT_TAGS = {
    "Large Language Model": ["AI", "LLM"],
    "Computer Architecture": ["Architecture", "Hardware"],
    "Machine Learning": ["AI", "ML"],
    "Backend Engineering": ["Backend", "Engineering"],
    "Distributed Systems": ["Architecture", "Systems"]
}

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5

LOG_LEVEL = "INFO"
