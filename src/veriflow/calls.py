"""Conservative lexical candidates, never proof of runtime reachability."""

from pathlib import PurePosixPath

from sqlalchemy import select

from veriflow.domain import VeriFlowError
from veriflow.indexing import published_index, snapshot_for_run
from veriflow.persistence import IndexedFile


def call_context(store, run_id, path, module_root=".", offset=0, limit=100):
    if not 1 <= limit <= 1000 or offset < 0:
        raise VeriFlowError("Invalid call query pagination")
    root = PurePosixPath(module_root)
    if root.is_absolute() or ".." in root.parts:
        raise VeriFlowError("Module root must be snapshot-relative")
    _, snapshot = snapshot_for_run(store, run_id)
    with store.transaction() as session:
        index = published_index(session, snapshot.id)

        def get_file(name):
            return session.scalar(
                select(IndexedFile).where(
                    IndexedFile.index_id == index.id, IndexedFile.path == name
                )
            )

        source = get_file(path)
        if source is None or source.result["status"] != "parsed":
            raise VeriFlowError("Call context requires an indexed Python file")
        try:
            PurePosixPath(path).relative_to(root)
        except ValueError:
            raise VeriFlowError("File is outside the selected module root") from None
        binding = source.result.get("bindings", {})
        items = []
        for call in source.result["calls"][offset : offset + limit]:
            target, name = source, call["expression"]
            eligible = not binding.get("unsafe", True)
            imports = binding.get("imports", {})
            for alias in sorted(imports, key=len, reverse=True):
                imported = imports[alias]
                if name == alias and imported["symbol"]:
                    name = imported["symbol"]
                elif name.startswith(alias + ".") and imported["symbol"] is None:
                    name = name[len(alias) + 1 :]
                else:
                    continue
                module = root / imported["module"].replace(".", "/")
                matches = [
                    item
                    for item in [
                        get_file(str(module) + ".py"),
                        get_file(str(module / "__init__.py")),
                    ]
                    if item is not None
                ]
                target = matches[0] if len(matches) == 1 else None
                break
            metadata = target.result.get("bindings", {}) if target else {}
            location = metadata.get("exports", {}).get(name)
            candidate = None
            if eligible and location and not metadata.get("unsafe", True):
                candidate = {
                    "snapshot_id": snapshot.id,
                    "path": target.path,
                    "sha256": target.result["sha256"],
                    "name": name,
                    **location,
                }
            items.append(
                {
                    **call,
                    "candidate": candidate,
                    "resolution": "static_candidate" if candidate else "unresolved",
                }
            )
    return {
        "schema_version": "1",
        "resolver_version": "1",
        "run_id": run_id,
        "index_id": index.id,
        "path": path,
        "module_root": str(root),
        "offset": offset,
        "limit": limit,
        "total": len(source.result["calls"]),
        "items": items,
        "reachability_proven": False,
        "assumptions": [
            "Selected module root matches runtime import search order.",
            "No monkey patching, import hooks or external rebinding.",
            "Candidate edges do not prove taint flow or runtime execution.",
        ],
    }
