"""Local SQLAlchemy persistence with explicit migrations and transaction control."""

import sqlite3
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from traceproof.domain import TraceProofError


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(String(200))
    classification: Mapped[str] = mapped_column(String(100))


class ImportBatch(Base):
    __tablename__ = "imports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    request_sha256: Mapped[str] = mapped_column(String(64))
    input_root: Mapped[str] = mapped_column(String(4096))
    created_at: Mapped[str] = mapped_column(String(40))


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    manifest: Mapped[dict] = mapped_column(JSON)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    state: Mapped[str] = mapped_column(String(30))
    profile: Mapped[str] = mapped_column(String(30))
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("snapshots.id"))
    created_at: Mapped[str] = mapped_column(String(40))


class ImportItem(Base):
    __tablename__ = "import_items"
    __table_args__ = (UniqueConstraint("import_id", "row_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    import_id: Mapped[str] = mapped_column(ForeignKey("imports.id"), index=True)
    row_number: Mapped[int]
    state: Mapped[str] = mapped_column(String(30), index=True)
    spec: Mapped[dict | None] = mapped_column(JSON)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"))
    error: Mapped[str | None] = mapped_column(String(2000))
    attempts: Mapped[int] = mapped_column(default=0)


class SourceIndex(Base):
    __tablename__ = "source_indexes"
    __table_args__ = (UniqueConstraint("snapshot_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"))
    version: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(30))
    report: Mapped[dict | None] = mapped_column(JSON)


class IndexedFile(Base):
    __tablename__ = "indexed_files"
    __table_args__ = (UniqueConstraint("index_id", "path"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    index_id: Mapped[str] = mapped_column(ForeignKey("source_indexes.id"), index=True)
    path: Mapped[str] = mapped_column(String(512))
    result: Mapped[dict] = mapped_column(JSON)


class CodeqlAttempt(Base):
    __tablename__ = "codeql_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    result: Mapped[dict] = mapped_column(JSON)


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.database = self.root / "traceproof.db"
        self.engine = create_engine(URL.create("sqlite", database=str(self.database)))

        @event.listens_for(self.engine, "connect")
        def configure(connection: sqlite3.Connection, _record):
            # SQLAlchemy owns BEGIN so DDL/reads participate in transactions too.
            connection.isolation_level = None
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")

        @event.listens_for(self.engine, "begin")
        def begin(connection):
            connection.exec_driver_sql("BEGIN")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.database) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
        config = Config()
        config.set_main_option("script_location", str(files("traceproof") / "migrations"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def require_initialized(self) -> None:
        if not self.database.is_file():
            raise TraceProofError("State is not initialized; run traceproof init first")

    @contextmanager
    def transaction(self):
        self.require_initialized()
        with self.sessions.begin() as session:
            yield session

    def close(self) -> None:
        self.engine.dispose()


@contextmanager
def exclusive_worker(root: Path):
    """One local worker; the OS releases ownership if the process dies.

    This is deliberately not a distributed lease or the production scheduler.
    """
    import fcntl

    with (root / "worker.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TraceProofError("A local worker already owns this state directory") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
