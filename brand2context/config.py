import os

LINK2CONTEXT_BASE = os.getenv("LINK2CONTEXT_URL", "http://67.209.190.54:8000")

# LLM Configuration — MiniMax M2.7
LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    "sk-cp-49r5TFMzeb7-z-HCbtIPK3h7NZPVs8QJIPVIBC9S3JDjeHq4pKU6YZ-srAyN1YH3-LR6wS0ot4f6xEcqR34SsBpE-yPuW-9kb_yGlDRaive4lhwduA3UAZs",
)
LLM_MODEL = os.getenv("LLM_MODEL", "MiniMax-M2.7")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://api.minimax.chat/v1/chat/completions")

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
