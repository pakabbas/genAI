import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_settings() -> dict[str, str | int]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    root_path = os.getenv("APP_ROOT_PATH", "").strip().rstrip("/")
    return {
        "gemini_api_key": api_key,
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-pro").strip(),
        "app_host": os.getenv("APP_HOST", "0.0.0.0"),
        "app_port": int(os.getenv("APP_PORT", "8000")),
        "app_root_path": root_path,
    }
