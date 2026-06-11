"""
Tatsu AI — Global Configuration
================================
All settings are centralized here. Override via environment variables or .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Deployment & Security ─────────────────────────────────────────────────────
DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "local")  # 'local' or 'cloud'
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin123")  # Default password for cloud login
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-tatsu-key-change-me")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
CHROMA_DIR = DATA_DIR / "chroma"
UI_DIR = BASE_DIR / "ui"

# Ensure runtime directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# ── LLM Settings ──────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # 'ollama' or 'openai'

# Ollama Settings (Local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3")

# OpenAI/Cloud Settings (OpenAI, Groq, Together, NVIDIA NIM, etc.)
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
# OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
# OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-ai/deepseek-v4-flash")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ── Agent Settings ─────────────────────────────────────────────────────────────
MAX_AGENT_ITERATIONS = int(os.getenv("MAX_AGENT_ITERATIONS", "10"))
AGENT_SYSTEM_PROMPT = """You are Tatsu, a powerful and helpful local AI assistant running on a Windows desktop.

Your capabilities:
- Answer questions and have conversations
- Perform calculations
- Open websites and applications
- Search for files and folders
- Manage files (create, move, rename, delete with confirmation)
- Report system information (CPU, RAM, disk, processes)
- Execute safe terminal commands
- Remember user preferences and past interactions
- Create multi-step plans for complex goals

Rules:
1. Always be helpful, concise, and accurate.
2. When using tools, explain what you're doing briefly.
3. For destructive actions (delete, install, system changes), ALWAYS ask for confirmation first.
4. If you're unsure, ask the user for clarification.
5. Never fabricate information — use tools to get real data.
6. When a task requires multiple steps, create a plan first, then execute step by step.
"""

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_PATH = str(DATA_DIR / "tatsu.db")

# ── Memory ─────────────────────────────────────────────────────────────────────
SHORT_TERM_MEMORY_LIMIT = int(os.getenv("SHORT_TERM_MEMORY_LIMIT", "50"))
CONVERSATION_CONTEXT_WINDOW = int(os.getenv("CONVERSATION_CONTEXT_WINDOW", "20"))

# ── Safety & Permissions ───────────────────────────────────────────────────────
CONFIRMATION_REQUIRED_ACTIONS = [
    "delete_file",
    "delete_folder",
    "install_software",
    "run_elevated_command",
    "modify_system_settings",
    "run_unknown_command",
]

ALLOWED_PATHS = [
    str(Path.home() / "Desktop"),
    str(Path.home() / "Documents"),
    str(Path.home() / "Downloads"),
    str(Path.home() / "Pictures"),
    str(Path.home() / "Videos"),
    str(Path.home() / "Music"),
]

BLOCKED_COMMANDS = [
    "format",
    "del /s",
    "rd /s",
    "rmdir /s",
    "rm -rf",
    "shutdown",
    "restart",
    "reg delete",
    "bcdedit",
    "diskpart",
    "cipher /w",
    "net user",
    "net localgroup",
    "schtasks /delete",
]

# ── Server ─────────────────────────────────────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
AUTO_OPEN_BROWSER = os.getenv("AUTO_OPEN_BROWSER", "true").lower() == "true"

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = str(LOG_DIR / "tatsu.log")
