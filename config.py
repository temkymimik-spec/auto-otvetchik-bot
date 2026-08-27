#!/usr/bin/env python3
"""Конфигурация: читается из переменных окружения Bothost или .env."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_dotenv_lite() -> None:
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_lite()


def env_int(*names: str, default: int = 0) -> int:
    for name in names:
        raw = os.getenv(name, "").strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                continue
    return default


def env_str(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


API_ID = env_int("API_ID", "TELEGRAM_API_ID")
API_HASH = env_str("API_HASH", "TELEGRAM_API_HASH")
BOT_TOKEN = env_str("BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "API_TOKEN")
ADMIN_ID = env_int("ADMIN_ID")

MAX_ACCOUNTS = env_int("MAX_ACCOUNTS", default=50) or 50
COOLDOWN = float(os.getenv("COOLDOWN", "10") or 10)
DEFAULT_REPLY = env_str(
    "DEFAULT_REPLY",
    default="Привет! Твоё сообщение получено. Отвечу в ближайшее время 🙂",
)

CONFIG_PATH = DATA_DIR / "autoreply_config.json"
ASSIGNED_PATH = DATA_DIR / "assigned.json"
SESSION_STRINGS_PATH = DATA_DIR / "sessions.json"

# служебные telegram-аккаунты: на них не отвечаем
SERVICE_IDS = {777000}