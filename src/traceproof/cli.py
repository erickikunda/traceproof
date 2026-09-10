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
        result = operation()
        typer.echo(result if isinstance(result, str) else render_json(result))
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
        return {"state_dir": str(ctx.obj.root), "schema": "0007", "status": "initialized"}

    perform(operation)


@app.command("index-run")
def index_run(ctx: typer.Context, run_id: str):
    """Build or resume a Python syntax index; does not discover vulnerabilities."""

    def operation():
        ctx.obj.require_initialized()
        with exclusive_worker(ctx.obj.root):
            return build_index(ctx.obj, run_id)

    perform(operation)


@app.command("record-review")
def record_review_command(
    ctx: typer.Context, repo_id: str, attempt_id: str, fingerprint: str, request: Path, key: str
):
    """Append an explicit operator assertion against exact candidate evidence."""
    from traceproof.reviews import read_review, record_review

    perform(
        lambda: record_review(ctx.obj, repo_id, attempt_id, fingerprint, read_review(request), key)
    )


@app.command("review-history")
def review_history_command(
    ctx: typer.Context,
    repo_id: str,
    attempt_id: str,
    fingerprint: str,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """Retrieve operator notes and revision without running analysis."""
    from traceproof.reviews import review_history

    perform(lambda: review_history(ctx.obj, repo_id, attempt_id, fingerprint, offset, limit))


@app.command("acceptance-run")
def acceptance_run_command(
    output_dir: Path, query: Path, timeout: Annotated[int, typer.Option(min=1, max=3600)] = 300
):
    """Run real CodeQL on isolated synthetic fixtures; no paid model calls."""
    from traceproof.acceptance import run_acceptance

    def operation():
        result = run_acceptance(output_dir, query, timeout)
        if not result["passed"]:
            typer.echo(render_json(result))
            raise typer.Exit(1)
        return result

    perform(operation)


@app.command("benchmark-schema")
def benchmark_schema_command():
    """Print the separate manifest and evaluator-label JSON schemas."""
    from traceproof.benchmark import BenchmarkLabels, BenchmarkManifest
    from traceproof.evaluation import EvaluationPlan

    perform(
        lambda: {
            "manifest": BenchmarkManifest.model_json_schema(),
            "labels": BenchmarkLabels.model_json_schema(),
            "evaluation_plan": EvaluationPlan.model_json_schema(),
        }
    )


@app.command("benchmark-evaluate")
def benchmark_evaluate_command(
    ctx: typer.Context, manifest: Path, labels: Path, plan: Path, format: str = "json"
):
    """Compare stored reports to evaluator-only labels without running scans."""
    from traceproof.evaluation import evaluate_benchmark, render_scorecard

    perform(lambda: render_scorecard(evaluate_benchmark(ctx.obj, manifest, labels, plan), format))


@app.command("benchmark-check")
def benchmark_check_command(
    ctx: typer.Context,
    manifest: Path,
    labels: Path | None = None,
    check_local_snapshots: bool = False,
):
    """Validate evaluator contracts; never dispatch scans or pass labels to models."""
    from traceproof.benchmark import check_benchmark

    def operation():
        result = check_benchmark(manifest, labels, ctx.obj if check_local_snapshots else None)
        if result["status"] != "valid_contract":
            typer.echo(render_json(result))
            raise typer.Exit(1)
        return result

    perform(operation)


@app.command("benchmark-publish")
def benchmark_publish_command(ctx: typer.Context, manifest: Path, labels: Path, plan: Path):
    """Evaluate pinned inputs and persist an immutable scorecard; no scans or model calls."""
    from traceproof.scorecards import publish_scorecard

    perform(lambda: publish_scorecard(ctx.obj, manifest, labels, plan))


@app.command("benchmark-get")
def benchmark_get_command(
    ctx: typer.Context, dataset_id: str, scorecard_id: str, format: str = "json"
):
    """Retrieve an exact stored scorecard without reading labels or reevaluating."""
    from traceproof.evaluation import render_scorecard
    from traceproof.scorecards import get_scorecard

    perform(lambda: render_scorecard(get_scorecard(ctx.obj, dataset_id, scorecard_id), format))


@app.command("benchmark-history")
def benchmark_history_command(
    ctx: typer.Context,
    dataset_id: str,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """List stored scorecard IDs for a dataset; does not evaluate or run scans."""
    from traceproof.scorecards import scorecard_history

    perform(lambda: scorecard_history(ctx.obj, dataset_id, offset, limit))


@app.command("publish-report")
def publish_report_command(
    ctx: typer.Context, repo_id: str, run_id: str | None = None, attempt_id: str | None = None
):
    """Materialize an immutable summary from stored state; no analysis or model calls."""
    from traceproof.reports import publish_report

    perform(lambda: publish_report(ctx.obj, repo_id, run_id, attempt_id))


@app.command("get-report")
def get_report_command(
    ctx: typer.Context,
    repo_id: str,
    report_id: str | None = None,
    run_id: str | None = None,
    format: str = "json",
):
    """Retrieve an exact report or the latest published version of the selected run."""
    from traceproof.reports import get_report, render_report

    perform(lambda: render_report(get_report(ctx.obj, repo_id, report_id, run_id), format))


@app.command("report-history")
def report_history_command(
    ctx: typer.Context,
    repo_id: str,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """List published report IDs without running analysis."""
    from traceproof.reports import report_history

    perform(lambda: report_history(ctx.obj, repo_id, offset, limit))


@app.command("resolve-report")
def resolve_report_command(ctx: typer.Context, repo_id: str, selection: str = "latest-attempt"):
    """Select a published report with current-work disclosure in a JSON envelope."""
    from traceproof.reports import resolve_report

    perform(lambda: resolve_report(ctx.obj, repo_id, selection))


@app.command("compare-reports")
def compare_reports_command(
    ctx: typer.Context, repo_id: str, baseline_id: str, current_id: str, format: str = "json"
):
    """Compare two exact reports without inferring fixes from missing observations."""
    from traceproof.comparison import compare_reports, render_comparison

    perform(
        lambda: render_comparison(
            compare_reports(ctx.obj, repo_id, baseline_id, current_id), format
        )
    )


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
def repo_report(
    ctx: typer.Context,
    repo_id: str,
    run_id: str | None = None,
    format: str = "json",
    index_id: str | None = None,
):
    """Retrieve coverage for a repo's latest admitted run, or an explicit historical run."""
    if format == "json":
        perform(lambda: repository_report(ctx.obj, repo_id, run_id, index_id))
    elif format == "markdown":
        try:
            typer.echo(report_markdown(repository_report(ctx.obj, repo_id, run_id, index_id)))
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
    ctx: typer.Context,
    run_id: str,
    timeout: Annotated[int, typer.Option(min=1, max=3600)] = 300,
    skip_baseline: Annotated[
        bool, typer.Option(help="Skip optional CodeQL line-count baseline")
    ] = False,
):
    """Opt-in local Python extraction; creates diagnostics, not security findings."""
    from traceproof.codeql import extract

    def operation():
        ctx.obj.require_initialized()
        with exclusive_worker(ctx.obj.root):
            return extract(ctx.obj, run_id, timeout, skip_baseline)

    perform(operation)


@app.command("codeql-status")
def codeql_status(ctx: typer.Context, attempt_id: str):
    """Retrieve an extraction attempt without executing CodeQL."""
    from traceproof.codeql import extraction_status

    perform(lambda: extraction_status(ctx.obj, attempt_id))


@app.command("source-evidence")
def evidence(
    ctx: typer.Context, run_id: str, path: str, line: int, end_line: int, sha256: str | None = None
):
    """Read at most 200 lines/32 KiB from verified snapshot source."""
    from traceproof.evidence import source_evidence

    perform(lambda: source_evidence(ctx.obj, run_id, path, line, end_line, sha256))


@app.command("call-context")
def calls(
    ctx: typer.Context,
    run_id: str,
    path: str,
    module_root: str = ".",
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """Retrieve conservative direct/import candidates; does not prove reachability."""
    from traceproof.calls import call_context

    perform(lambda: call_context(ctx.obj, run_id, path, module_root, offset, limit))


@app.command("codeql-analyze")
def codeql_analyze(
    ctx: typer.Context,
    extraction_id: str,
    queries: Path,
    timeout: Annotated[int, typer.Option(min=1, max=3600)] = 600,
):
    """Run an operator-provided local query/suite; publish unreviewed SARIF candidates."""
    from traceproof.scanning import analyze

    def operation():
        ctx.obj.require_initialized()
        with exclusive_worker(ctx.obj.root):
            return analyze(ctx.obj, extraction_id, queries, timeout)

    perform(operation)


@app.command("scan-report")
def scan_report_command(
    ctx: typer.Context,
    repo_id: str,
    run_id: str | None = None,
    attempt_id: str | None = None,
    format: str = "json",
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """Read the latest static-analysis attempt, or an explicitly selected attempt."""
    from traceproof.scanning import scan_report, scan_report_markdown

    def operation():
        if format not in {"json", "markdown"}:
            raise TraceProofError("Format must be json or markdown")
        report = scan_report(ctx.obj, repo_id, run_id, attempt_id, offset, limit)
        return scan_report_markdown(report) if format == "markdown" else report

    perform(operation)


@app.command("build-bundle")
def bundle_build(ctx: typer.Context, attempt_id: str, fingerprint: str):
    """Materialize bounded primary/flow evidence for one static candidate."""
    from traceproof.bundles import build_bundle

    perform(lambda: build_bundle(ctx.obj, attempt_id, fingerprint))


@app.command("bundle-status")
def bundle_status(ctx: typer.Context, bundle_id: str):
    """Retrieve a materialized evidence bundle without reading source or invoking a model."""
    from traceproof.bundles import get_bundle

    perform(lambda: get_bundle(ctx.obj, bundle_id))


@app.command("expand-bundle")
def bundle_expand(ctx: typer.Context, bundle_id: str, request: Path):
    """Add explicitly requested context within the original bundle's fixed byte budget."""
    from traceproof.expansion import expand_bundle, read_expansion

    perform(lambda: expand_bundle(ctx.obj, bundle_id, read_expansion(request)))


@app.command("evidence-policy")
def evidence_policy(ctx: typer.Context, rule_id: str):
    """Show supported evidence obligations for a CodeQL rule."""
    from traceproof.claims import requirements

    perform(lambda: requirements(rule_id))


@app.command("check-evidence")
def evidence_check(ctx: typer.Context, bundle_id: str, decision: Path):
    """Validate a decision's claims against a materialized bundle; no provider invocation."""
    from pydantic import ValidationError

    from traceproof.bundles import get_bundle
    from traceproof.claims import assess_evidence
    from traceproof.models import Decision

    def operation():
        with decision.open("rb") as handle:
            raw = handle.read(32 * 1024 + 1)
        if len(raw) > 32 * 1024:
            raise TraceProofError("Decision exceeds the 32 KiB limit")
        try:
            parsed = Decision.model_validate_json(raw)
        except ValidationError:
            raise TraceProofError("Decision does not match the supported claim schema") from None
        return assess_evidence(get_bundle(ctx.obj, bundle_id), parsed)

    perform(operation)


@app.command("triage-budget")
def budget_set(ctx: typer.Context, run_id: str, micro_usd: int):
    """Set an immutable per-run triage cap; 1,000,000 micro-USD equals one USD."""
    from traceproof.triage import set_budget

    perform(lambda: set_budget(ctx.obj, run_id, micro_usd))


@app.command("triage")
def triage_command(
    ctx: typer.Context, bundle_id: str, config: Path, key: str, replay: Path | None = None
):
    """Triage one bundle; replay is offline and live providers require explicit opt-in."""
    from traceproof.models import ReplayAdapter, live_adapter, read_config
    from traceproof.triage import triage

    def operation():
        policy = read_config(config)
        if policy.provider == "replay":
            if replay is None:
                raise TraceProofError("Replay policy requires --replay RESPONSE_JSON")
            adapter = ReplayAdapter(replay)
        else:
            if replay is not None:
                raise TraceProofError("A live policy cannot use a replay fixture")
            adapter = live_adapter(policy)
        return triage(ctx.obj, bundle_id, policy, adapter, key)

    perform(operation)


@app.command("triage-report")
def triage_status(
    ctx: typer.Context,
    run_id: str,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """Retrieve advisory decisions and the durable cost ledger without model calls."""
    from traceproof.triage import triage_report

    perform(lambda: triage_report(ctx.obj, run_id, offset, limit))


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


@app.command("run-history")
def run_history_command(
    ctx: typer.Context,
    repo_id: str,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """List admitted runs, including work without a scan or published report."""
    from traceproof.history import run_history

    perform(lambda: run_history(ctx.obj, repo_id, offset, limit))


@app.command("scan-history")
def scan_history_command(
    ctx: typer.Context,
    repo_id: str,
    run_id: str | None = None,
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
):
    """List query attempts, including failed and unpublished work; never executes scans."""
    from traceproof.history import scan_history

    perform(lambda: scan_history(ctx.obj, repo_id, run_id, offset, limit))


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
