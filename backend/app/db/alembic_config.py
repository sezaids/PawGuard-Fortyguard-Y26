"""Helpers for safely passing runtime values into Alembic's ConfigParser."""


def escape_configparser_value(value: str) -> str:
    """Escape percent signs because Alembic's ConfigParser interpolates them.

    PostgreSQL URLs commonly percent-encode password characters (for example
    ``%40`` for ``@``). ConfigParser treats a bare percent sign as interpolation
    syntax, so doubling it preserves the original URL when Alembic reads it.
    """

    return value.replace("%", "%%")
