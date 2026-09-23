"""Trusted, explicit backend registry; repository metadata cannot load adapters."""

from dataclasses import asdict, dataclass

from veriflow.codeql import extract, extraction_status
from veriflow.codeql_scanner import execute
from veriflow.domain import VeriFlowError
from veriflow.scanner import ScannerExecutor


@dataclass(frozen=True)
class Backend:
    engine_id: str
    adapter_version: str
    input_kind: str
    output_format: str
    executor: ScannerExecutor

    def prepare(self, store, run_id, **options):
        """Creation stays within the selected engine and its approved profiles."""
        if self.engine_id != "codeql" or self.input_kind != "codeql_database":
            raise VeriFlowError("Prepared-input adapter is not implemented")
        return extract(store, run_id, **options)

    def prepared(self, store, preparation_id):
        """Resolve only this backend's durable preparation store."""
        if self.engine_id != "codeql" or self.input_kind != "codeql_database":
            raise VeriFlowError("Prepared-input adapter is not implemented")
        result = extraction_status(store, preparation_id)
        if result.get("status") != "extracted":
            raise VeriFlowError("Security queries require a successful extraction")
        return result

    def metadata(self):
        return {
            "engine_id": self.engine_id,
            "adapter_version": self.adapter_version,
            "output_format": self.output_format,
            "version": None,
            "capabilities": {
                "may_emit_flow_paths": True,
                "flow_paths_guaranteed": False,
                "coverage_verified": False,
            },
        }


@dataclass(frozen=True)
class PreparedInput:
    engine_id: str
    kind: str
    preparation_id: str
    run_id: str
    snapshot_id: str
    tool_version: str

    def metadata(self):
        return asdict(self)


def backend_for(engine_id: str = "codeql") -> Backend:
    if engine_id != "codeql":
        raise VeriFlowError(f"Scanner backend is not implemented: {engine_id}")
    return Backend("codeql", "1", "codeql_database", "sarif-2.1.0", execute)
