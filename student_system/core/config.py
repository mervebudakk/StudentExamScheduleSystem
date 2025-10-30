from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path

load_dotenv(find_dotenv(), override=False)


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def psycopg2_params(self) -> dict:
        return {
            'host': self.host,
            'port': self.port,
            'dbname': self.name,
            'user': self.user,
            'password': self.password
        }


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "Dinamik Sınav Takvimi Sistemi"
    version: str = "1.0.0"
    debug: bool = False


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "sinav_sistemi"),
        user=os.getenv("DB_USER", "postgres"),
        password=(os.getenv("DB_PASS") or os.getenv("DB_PASSWORD") or "")
    )


def get_app_settings() -> AppSettings:
    return AppSettings(
        debug=os.getenv("DEBUG", "False").lower() == "true"
    )

db_settings = get_database_settings()
app_settings = get_app_settings()

if __name__ == "__main__":
    print("=" * 60)
    print("VERİTABANI AYARLARI")
    print("=" * 60)
    print(f"Host:     {db_settings.host}")
    print(f"Port:     {db_settings.port}")
    print(f"Database: {db_settings.name}")
    print(f"User:     {db_settings.user}")
    print(f"Password: {'*' * len(db_settings.password)}")
    print("=" * 60)
    print(f"\nConnection String:")
    print(db_settings.connection_string)
    print("=" * 60)