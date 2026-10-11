import os

from dotenv import load_dotenv

load_dotenv()


def get_settings() -> dict[str, str | int]:
    """Env-only settings (no forever cache — DB-backed prefs live in settings_service)."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    root_path = os.getenv("APP_ROOT_PATH", "").strip().rstrip("/")
    return {
        "gemini_api_key": api_key,
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip(),
        "app_root_path": root_path,
        "db_host": os.getenv("DB_HOST", "127.0.0.1").strip(),
        "db_port": int(os.getenv("DB_PORT", "3306")),
        "db_name": os.getenv("DB_NAME", "leadpilot").strip(),
        "db_user": os.getenv("DB_USER", "leadpilot").strip(),
        "db_password": os.getenv("DB_PASSWORD", "").strip(),
    }
