"""Alembic environment.

Takes its URL from application settings (never a hardcoded string) and uses the
read-write engine, because migrations write by definition.

`render_as_batch=True` is required for SQLite: it has no full ALTER TABLE, so
Alembic emulates column changes by copying the table. It is harmless on
Postgres, so the same migrations run unchanged on both.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401  — registers every table on Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().app_database_url)
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Render our custom column types with an import Alembic actually emits.

    Without this, autogenerate writes `app.models.types.UTCDateTime()` into the
    migration but adds no corresponding import, and `alembic upgrade` dies with
    NameError. Registering the import here fixes it for every future migration
    rather than for one generated file.
    """
    if type_ == "type" and obj.__class__.__module__.startswith("app.models"):
        autogen_context.imports.add("import app.models.types")
    return False  # fall through to Alembic's default rendering


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
