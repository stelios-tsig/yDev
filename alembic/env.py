import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Πρόσβαση στο project (models.py, database.py) ---------------------------
# Το alembic τρέχει με cwd τη ρίζα του project, αλλά το βάζουμε ρητά στο path
# ώστε να δουλεύει και όταν καλείται από αλλού.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# Το Base είναι το declarative base του project. Το `import models` καταχωρεί
# ΟΛΑ τα μοντέλα (User, Project, Technology, Version, Comment, Rating + το
# association table) πάνω στο Base.metadata, ώστε το --autogenerate να τα βλέπει.
from database import Base  # noqa: E402
import models  # noqa: E402,F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Το URL της βάσης έρχεται από το ίδιο DATABASE_URL που χρησιμοποιεί το app
# (PostgreSQL σε production, SQLite fallback τοπικά). Το '%' γίνεται escape
# γιατί το ConfigParser του alembic.ini το ερμηνεύει ως interpolation token.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ydev.db")
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # Το SQLite δεν υποστηρίζει ALTER TABLE πλήρως· το batch mode
            # αναδημιουργεί τον πίνακα όταν χρειάζεται.
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
