from alembic.config import Config

from app.core.config import Settings
from app.db.alembic_config import escape_configparser_value


def test_standard_supabase_postgres_url_uses_installed_psycopg_driver():
    settings = Settings(database_url="postgresql://postgres:password@db.example.supabase.co:5432/postgres?sslmode=require")
    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.sqlalchemy_database_url


def test_legacy_postgres_scheme_is_normalized():
    settings = Settings(database_url="postgres://user:password@db.example/pawguard")
    assert settings.sqlalchemy_database_url == "postgresql+psycopg://user:password@db.example/pawguard"


def test_percent_encoded_database_url_can_be_read_by_alembic_config():
    database_url = "postgresql+psycopg://user:p%40ss%25word@db.example/pawguard?sslmode=require"
    config = Config()

    config.set_main_option("sqlalchemy.url", escape_configparser_value(database_url))

    assert config.get_main_option("sqlalchemy.url") == database_url
