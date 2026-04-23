import os
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import your models' Base and metadata
from backend.models import Base, get_database_url

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set database URL from environment
database_url = get_database_url()
config.set_main_option("sqlalchemy.url", database_url)

# Import all models for autogenerate support
from backend.models import AgentModel, CallModel, TranscriptModel, WebhookLogModel, ChatAgentModel, FunctionModel, PhoneNumberModel

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Only run migrations online if we can connect to the database
    try:
        run_migrations_online()
    except Exception as e:
        # If database is not available, skip online migrations
        # This allows alembic revision to work without DB connection
        if "revision" in str(context.config.cmd_opts):
            print(f"Database not available, skipping online migrations: {e}")
        else:
            raise
