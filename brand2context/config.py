import os

LINK2CONTEXT_BASE = os.getenv("LINK2CONTEXT_URL", "http://67.209.190.54:8000")
MINIMAX_API_KEY = os.getenv(
    "MINIMAX_API_KEY",
    "sk-cp-49r5TFMzeb7-z-HCbtIPK3h7NZPVs8QJIPVIBC9S3JDjeHq4pKU6YZ-srAyN1YH3-LR6wS0ot4f6xEcqR34SsBpE-yPuW-9kb_yGlDRaive4lhwduA3UAZs",
)
MINIMAX_MODEL = "MiniMax-M2.7"
MINIMAX_ENDPOINT = "https://api.minimax.chat/v1/text/chatcompletion_v2"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"
MAX_CRAWL_PAGES = 20
SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "schema", "brand_knowledge.schema.json"
)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
MEDIACRAWLER_PATH = os.getenv("MEDIACRAWLER_PATH", "/opt/MediaCrawler")
SOCIAL_PLATFORMS = ["wb", "xhs", "dy"]
SOCIAL_CRAWL_TIMEOUT = 120
