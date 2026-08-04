import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

INTERVIEWER_MODEL = "gpt-4o"
#"claude-sonnet-4-6"
EXTRACTION_MODEL = "gpt-4o"
#"claude-haiku-4-5"
SUMMARIZATION_MODEL = "gpt-4o-mini"
#"claude-haiku-4-5"

PROMPT_VERSION = "v0.2.0"
MAX_FOLLOW_UP_DEPTH = 2
SUMMARIZATION_TOKEN_THRESHOLD = 3000

DB_PATH = "interview_agent.db"
