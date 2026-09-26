import csv
import zipfile

import pytest

from veriflow.persistence import Store


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path / "state")
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / "inputs"
    root.mkdir()
    path = root / "source.zip"
    with zipfile.ZipFile(path, "w") as out:
        out.writestr("project/app.py", "def greet(name):\n    return name\n")
        out.writestr("project/README.md", "Synthetic test input\n")
    return path


@pytest.fixture
def manifest(tmp_path):
    def write(rows, fields=None):
        path = tmp_path / "repos.csv"
        with path.open("w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fields or list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    return write


def row(archive, **overrides):
    return {
        "repo_id": "example",
        "source_type": "pvc",
        "source_uri": str(archive),
        "owner": "tests",
        "classification": "synthetic",
        **overrides,
    }
