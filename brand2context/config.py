import os

LINK2CONTEXT_BASE = os.getenv("LINK2CONTEXT_URL", "http://67.209.190.54:8000")

# LLM Configuration — GLM-4-Flash (free, unlimited)
LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    "63078dbeb7e0b19197c7a44e64b7228e.4IPyp2wgiLZMhKAb",
)
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-flash")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://open.bigmodel.cn/api/paas/v4/chat/completions")

# Legacy aliases (for backward compatibility with llm.py etc.)
MINIMAX_API_KEY = LLM_API_KEY
MINIMAX_MODEL = LLM_MODEL
MINIMAX_ENDPOINT = LLM_ENDPOINT
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"
METASO_API_KEY = os.getenv("METASO_API_KEY", "mk-DA5C2447D54689CD7757A0C4AB162CA3")
METASO_SEARCH_ENDPOINT = "https://metaso.cn/api/v1/search"
METASO_READER_ENDPOINT = "https://metaso.cn/api/v1/reader"
MAX_CRAWL_PAGES = 30
SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "schema", "brand_knowledge.schema.json"
)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
MEDIACRAWLER_PATH = os.getenv("MEDIACRAWLER_PATH", "/opt/MediaCrawler")
SOCIAL_PLATFORMS = ["wb", "xhs", "dy"]
SOCIAL_CRAWL_TIMEOUT = 120
