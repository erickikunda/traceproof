"""Render namespaced Kubernetes JSON; never contacts a cluster or creates storage."""

import argparse
import json
import re
from pathlib import Path

PROFILES = json.loads(
    (Path(__file__).resolve().parents[1] / "containers/ocp-smoke-profiles.json").read_text()
)

for _language in ("csharp", "rust"):
    PROFILES.update(
        json.loads(
            (
                Path(__file__).resolve().parents[1]
                / f"containers/ocp-smoke-{_language}-profiles.json"
            ).read_text()
        )
    )


def bundle(namespace, name, image, input_pvc, reports_pvc, language="c", batch_max_rows=None):
    if batch_max_rows is not None and not 1 <= batch_max_rows <= 10:
        raise ValueError("Batch limit must be 1–10")
    if language not in PROFILES:
        raise ValueError("Unsupported smoke language/toolchain")
    for value in (namespace, name, input_pvc, reports_pvc):
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", value):
            raise ValueError("Names must be DNS labels of at most 63 characters")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9./:_-]*@sha256:[a-f0-9]{64}", image):
        raise ValueError("A registry image pinned by SHA-256 digest is required")
    if input_pvc == reports_pvc:
        raise ValueError("Use separate input and report PVCs")
    labels = {"app.kubernetes.io/name": "traceproof-smoke", "traceproof-job": name}
    metadata = {"name": name, "namespace": namespace}
    return {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": metadata,
                "automountServiceAccountToken": False,
            },
            {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": metadata,
                "spec": {
                    "podSelector": {"matchLabels": labels},
                    "policyTypes": ["Ingress", "Egress"],
                    "ingress": [],
                    "egress": [],
                },
            },
            {
                "apiVersion": "batch/v1",
                "kind": "Job",
                "metadata": metadata,
                "spec": {
                    "backoffLimit": 0,
                    "activeDeadlineSeconds": 600
                    if batch_max_rows is None
                    else batch_max_rows * 360 + 300,
                    "parallelism": 1,
                    "completions": 1,
                    "template": {
                        "metadata": {"labels": labels},
                        "spec": {
                            "serviceAccountName": name,
                            "automountServiceAccountToken": False,
                            "restartPolicy": "Never",
                            "enableServiceLinks": False,
                            "nodeSelector": {"kubernetes.io/arch": "arm64"},
                            "securityContext": {
                                "runAsNonRoot": True,
                                "seccompProfile": {"type": "RuntimeDefault"},
                            },
                            "containers": [
                                {
                                    "name": "scan",
                                    "image": image,
                                    "imagePullPolicy": "IfNotPresent",
                                    "args": ["--language", language]
                                    + (
                                        []
                                        if batch_max_rows is None
                                        else ["--max-rows", str(batch_max_rows)]
                                    ),
                                    "command": [
                                        "/opt/traceproof-venv/bin/python",
                                        "/opt/traceproof/ocp_smoke.py"
                                        if batch_max_rows is None
                                        else "/opt/traceproof/ocp_archive_batch.py",
                                    ],
                                    "env": [
                                        {
                                            "name": "TRACEPROOF_EXECUTION_ID",
                                            "valueFrom": {
                                                "fieldRef": {"fieldPath": "metadata.uid"}
                                            },
                                        }
                                    ],
                                    "securityContext": {
                                        "allowPrivilegeEscalation": False,
                                        "readOnlyRootFilesystem": True,
                                        "capabilities": {"drop": ["ALL"]},
                                    },
                                    "resources": {
                                        "requests": {
                                            "cpu": "1",
                                            "memory": "2Gi",
                                            "ephemeral-storage": "2Gi",
                                        },
                                        "limits": {
                                            "cpu": "2",
                                            "memory": "4Gi",
                                            "ephemeral-storage": "8Gi",
                                        },
                                    },
                                    "volumeMounts": [
                                        {"name": "input", "mountPath": "/input", "readOnly": True},
                                        {"name": "reports", "mountPath": "/reports"},
                                        {"name": "work", "mountPath": "/work"},
                                        {"name": "tmp", "mountPath": "/tmp"},
                                    ],
                                }
                            ],
                            "volumes": [
                                {
                                    "name": "input",
                                    "persistentVolumeClaim": {
                                        "claimName": input_pvc,
                                        "readOnly": True,
                                    },
                                },
                                {
                                    "name": "reports",
                                    "persistentVolumeClaim": {"claimName": reports_pvc},
                                },
                                {"name": "work", "emptyDir": {"sizeLimit": "6Gi"}},
                                {"name": "tmp", "emptyDir": {"sizeLimit": "1Gi"}},
                            ],
                        },
                    },
                },
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("namespace", "name", "image", "input-pvc", "reports-pvc"):
        parser.add_argument(f"--{flag}", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", choices=sorted(PROFILES), default="c")
    parser.add_argument("--batch-max-rows", type=int)
    args = parser.parse_args()
    data = bundle(
        args.namespace,
        args.name,
        args.image,
        args.input_pvc,
        args.reports_pvc,
        args.language,
        args.batch_max_rows,
    )
    with args.output.open("x") as target:
        json.dump(data, target, indent=2)
        target.write("\n")


if __name__ == "__main__":
    main()
