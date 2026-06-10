import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config object
config = context.config

# Set up loggers from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DB_PATH env var
db_path = os.environ.get("DB_PATH", "/data/app.db")
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

# Import Base and all models so autogenerate can see the full schema.
# Models must be imported AFTER the URL is set so database.py can use settings.
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401 — registers all models on Base.metadata

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
