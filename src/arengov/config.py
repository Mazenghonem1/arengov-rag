from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SNAPSHOT_ROOT = DATA_DIR / "snapshots"
INDEX_ROOT = DATA_DIR / "index"
EVAL_DIR = ROOT / "eval"
INDEX_VERSION_FILE = EVAL_DIR / "index_version.txt"
