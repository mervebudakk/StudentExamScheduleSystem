# student_system/core/config.py
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv(), override=False)

@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    name: str
    user: str
    password: str

def get_settings() -> Settings:
    return Settings(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", ""),
        user=os.getenv("DB_USER", ""),
        password=(os.getenv("DB_PASS") or os.getenv("DB_PASSWORD") or "")
    )
