import os
from pathlib import Path

DATA_DIR = Path("data")
def get_api_key() -> str:
    return os.environ.get("API_KEY", "")
AUTH_PREFIXES: set[str] = set()
