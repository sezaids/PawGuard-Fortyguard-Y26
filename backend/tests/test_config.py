from app.core.config import Settings


def test_standard_supabase_postgres_url_uses_installed_psycopg_driver():
    settings = Settings(database_url="postgresql://postgres:password@db.example.supabase.co:5432/postgres?sslmode=require")
    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.sqlalchemy_database_url


def test_legacy_postgres_scheme_is_normalized():
    settings = Settings(database_url="postgres://user:password@db.example/pawguard")
    assert settings.sqlalchemy_database_url == "postgresql+psycopg://user:password@db.example/pawguard"
