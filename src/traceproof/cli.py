"""Local operator CLI. JSON or requested Markdown; errors never echo source contents."""

from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.exc import SQLAlchemyError

from traceproof.artifacts import ArtifactStore
from traceproof.domain import TraceProofError
from traceproof.indexing import build_index, query_index, report_markdown, repository_report
from traceproof.intake import import_status, process, render_json, run_status, submit
from traceproof.persistence import Store, exclusive_worker

app = typer.Typer(no_args_is_help=True, help="TraceProof — local intake and Python coverage")


@app.callback()
def configure(
    ctx: typer.Context,
    state_dir: Annotated[
        Path, typer.Option(help="Local state directory; never use shared network storage")
    ] = Path(".traceproof"),
):
    ctx.obj = Store(state_dir)
    ctx.call_on_close(ctx.obj.close)


def perform(operation):
    try:
        typer.echo(render_json(operation()))
    except TraceProofError as exc:
        typer.echo(render_json({"error": str(exc)}), err=True)
        raise typer.Exit(1) from exc
    except (OSError, SQLAlchemyError):
        typer.echo(
            render_json(
                {"error": "Local storage operation failed; check paths and initialization"}
            ),
            err=True,
        )
        raise typer.Exit(1) from None


@app.command()
def init(ctx: typer.Context):
    """Initialize or upgrade the local SQLite schema."""

    def operation():
        ctx.obj.initialize()
        return {"state_dir": str(ctx.obj.root), "schema": "0002", "status": "initialized"}

    perform(operation)


@app.command("index-run")
def index_run(ctx: typer.Context, run_id: str):
    """Build or resume a Python syntax index; does not discover vulnerabilities."""

    def operation():
        ctx.obj.require_initialized()
        with exclusive_worker(ctx.obj.root):
            return build_index(ctx.obj, run_id)

    perform(operation)


@app.command("query-index")
def index_query(
    ctx: typer.Context,
    run_id: str,
    kind: str = "symbols",
    path: str | None = None,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """Retrieve paginated symbols or unresolved calls with immutable evidence references."""
    perform(lambda: query_index(ctx.obj, run_id, kind, path, offset, limit))


@app.command("repo-report")
def repo_report(ctx: typer.Context, repo_id: str, run_id: str | None = None, format: str = "json"):
    """Retrieve coverage for a repo's latest admitted run, or an explicit historical run."""
    if format == "json":
        perform(lambda: repository_report(ctx.obj, repo_id, run_id))
    elif format == "markdown":
        try:
            typer.echo(report_markdown(repository_report(ctx.obj, repo_id, run_id)))
        except (TraceProofError, OSError, SQLAlchemyError):
            typer.echo(
                "Cannot retrieve report; check repository, run, and initialization.", err=True
            )
            raise typer.Exit(1) from None
    else:
        typer.echo("Format must be json or markdown", err=True)
        raise typer.Exit(1)


@app.command("codeql-extract")
def codeql_extract(
    ctx: typer.Context, run_id: str, timeout: Annotated[int, typer.Option(min=1, max=3600)] = 300
):
    """Opt-in local Python extraction; creates diagnostics, not security findings."""
    from traceproof.codeql import extract

    def operation():
        ctx.obj.require_initialized()
        with exclusive_worker(ctx.obj.root):
            return extract(ctx.obj, run_id, timeout)

    perform(operation)


@app.command("codeql-status")
def codeql_status(ctx: typer.Context, attempt_id: str):
    """Retrieve an extraction attempt without executing CodeQL."""
    from traceproof.codeql import extraction_status

    perform(lambda: extraction_status(ctx.obj, attempt_id))


@app.command("import-csv")
def import_csv(
    ctx: typer.Context,
    manifest: Path,
    input_root: Annotated[
        Path, typer.Option(help="Only archives under this absolute root are allowed")
    ],
    key: Annotated[str, typer.Option(help="Stable idempotency key for this submission")],
):
    """Admit local TAR/TAR.GZ/ZIP rows; process them separately with worker."""
    perform(lambda: import_status(ctx.obj, submit(ctx.obj, manifest, input_root, key)))


@app.command("import-status")
def status(ctx: typer.Context, import_id: str):
    """Retrieve durable per-row results without processing source."""
    perform(lambda: import_status(ctx.obj, import_id))


@app.command("run-status")
def run(ctx: typer.Context, run_id: str):
    """Retrieve an intake run; snapshot readiness does not imply a security scan."""
    perform(lambda: run_status(ctx.obj, run_id))


@app.command()
def worker(
    ctx: typer.Context,
    import_id: str,
    max_items: Annotated[int, typer.Option(min=1, max=1000)] = 1000,
):
    """Capture admitted archives; restart this command to resume interrupted intake."""

    def operation():
        store = ctx.obj
        store.require_initialized()
        with exclusive_worker(store.root):
            return process(store, ArtifactStore(store.root), import_id, max_items)

    perform(operation)


@app.command("verify-snapshot")
def verify(ctx: typer.Context, snapshot_id: str):
    """Recheck the manifest, original archive and every source-file digest."""

    def operation():
        ctx.obj.require_initialized()
        manifest = ArtifactStore(ctx.obj.root).verify(snapshot_id)
        return {"snapshot_id": manifest.snapshot_id, "files": len(manifest.files), "valid": True}

    perform(operation)
