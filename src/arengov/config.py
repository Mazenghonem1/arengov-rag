import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SNAPSHOT_ROOT = DATA_DIR / "snapshots"
INDEX_ROOT = DATA_DIR / "index"
EVAL_DIR = ROOT / "eval"
INDEX_VERSION_FILE = EVAL_DIR / "index_version.txt"

# Crawl (phase 01)
BASE_URL = "https://u.ae"
CATEGORIES = ("visa-and-emirates-id", "jobs", "business")
CRAWL_DELAY_S = 3.0
CRAWL_MAX_DEPTH = 4
CRAWL_MAX_EN_PER_CATEGORY = 70
CRAWL_MAX_CONSECUTIVE_ERRORS = 3
CRAWL_TIMEOUT_S = 30
USER_AGENT = (
    "ArEnGovRAG/0.1 (+https://github.com/Mazenghonem1/arengov-rag; non-commercial research)"
)

# Clean + chunk (phase 02)
MIN_PAGE_CHARS = 200
CHUNK_MAX_TOKENS = 400
TOKENIZER_MODEL = "BAAI/bge-m3"

# BM25 (phase 03)
BM25_K1 = 1.5
BM25_B = 0.75
BM25_TOP_N = 50
TOP_K_CONTEXT = 5

# LLM + generation (phase 04)
LLM_BACKEND = os.environ.get("LLM_BACKEND", "openai")
GEN_MODEL = "gpt-6-luna"
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-6.1-terra")
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
REASONING_EFFORT = "none"  # lowest value gpt-6-luna accepts (probed phase 04)
GEN_MAX_TOKENS = 1024
PRICES_PER_M = {"gpt-6-luna": (0.10, 0.50), "gpt-6.1-terra": (1.00, 5.00)}
SNIPPET_MAX_CHARS = 300

# Judge (phase 07)
JUDGE_MAX_TOKENS = 800

# Dense + hybrid (phase 08)
EMBED_MODEL = "BAAI/bge-m3"
DENSE_TOP_N = 50
RRF_K = 60
FUSED_TOP_N = 20

# Rerank + gate (phase 09)
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_TOP_N = 20
RERANK_MAX_LENGTH = 512
GATE_TAU = 0.298  # pick-tau on dev: F1 0.83, refuses 1/27 answerable
