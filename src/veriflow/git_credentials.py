"""Operator-provided, exact-repository HTTPS Basic credentials for acquisition only."""

import base64
import json
from pathlib import Path

from veriflow.domain import VeriFlowError


def read_credentials(path):
    if path is None:
        return None
    try:
        with Path(path).open("rb") as source:
            raw = source.read(16385)
        if len(raw) > 16384:
            raise ValueError
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"url", "username", "password"}:
            raise ValueError
        if any(
            not isinstance(v, str) or not v or any(ord(c) < 32 or ord(c) == 127 for c in v)
            for v in value.values()
        ):
            raise ValueError
        if ":" in value["username"]:
            raise ValueError
        return value
    except (OSError, ValueError, UnicodeError):
        raise VeriFlowError(
            "Credential file requires bounded JSON with url, username and password"
        ) from None


def credential_environment(credentials, url):
    if credentials is None:
        return {}
    if credentials["url"] != url:
        raise VeriFlowError("Credential repository URL does not match acquisition URL")
    token = base64.b64encode(
        (credentials["username"] + ":" + credentials["password"]).encode("utf-8")
    ).decode("ascii")
    # Git's environment config avoids secrets in argv, on disk, or in repository config.
    # The process environment remains sensitive to same-user/privileged inspection.
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"http.{url}.extraHeader",
        "GIT_CONFIG_VALUE_0": f"Authorization: Basic {token}",
    }
