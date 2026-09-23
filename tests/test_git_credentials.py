import base64
import functools
import json
import ssl
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from veriflow.domain import TraceProofError
from veriflow.git_acquisition import Git, acquire
from veriflow.git_credentials import credential_environment, read_credentials
from veriflow.git_transport import configure, transport_settings


def test_wrong_repository_fails_before_output(tmp_path):
    path = tmp_path / "credential.json"
    path.write_text(
        json.dumps(dict(url="https://approved.invalid/one", username="test", password="synthetic"))
    )
    with pytest.raises(TraceProofError, match="does not match"):
        acquire(
            "https://approved.invalid/two",
            "refs/heads/main",
            ["approved.invalid"],
            tmp_path / "out",
            "repo",
            "team",
            "public",
            credential_file=path,
        )
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"url": "x", "username": "a:b", "password": "secret"},
        {"url": "x", "username": "u", "password": "secret\n"},
    ],
)
def test_invalid_credentials_sanitized(tmp_path, value):
    path = tmp_path / "credential.json"
    path.write_text(json.dumps(value))
    with pytest.raises(TraceProofError) as error:
        read_credentials(path)
    assert "secret" not in str(error.value)


def test_native_https_private_fetch(tmp_path):
    def run(*args):
        return subprocess.run(
            args, check=True, capture_output=True
        ).stdout

    source = tmp_path / "source"
    run("git", "init", "-b", "main", str(source))
    (source / "example.txt").write_text("synthetic private source")
    run("git", "-C", str(source), "add", ".")
    run(
        "git",
        "-C",
        str(source),
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    web = tmp_path / "web"
    web.mkdir()
    run("git", "clone", "--bare", str(source), str(web / "repo.git"))
    run("git", "--git-dir=" + str(web / "repo.git"), "update-server-info")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    run(
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(key),
        "-out",
        str(cert),
        "-days",
        "1",
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost",
    )
    expected = "Basic " + base64.b64encode(b"fixture:synthetic-token").decode()
    statuses = []

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Authorization") != expected:
                statuses.append(401)
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
                self.end_headers()
                return
            statuses.append(200)
            super().do_GET()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"https://localhost:{server.server_port}/repo.git"
    try:
        for name, password, ca, success in [
            ("good", "synthetic-token", cert, True),
            ("bad", "wrong", cert, False),
            ("untrusted", "synthetic-token", None, False),
        ]:
            root = tmp_path / name
            root.mkdir()
            git = Git(root, 15)
            configure(git, transport_settings(ca))
            git.auth_env = credential_environment(
                dict(url=url, username="fixture", password=password), url
            )
            git.call("init", "--bare", "--template=", "repo.git")
            assert "synthetic-token" not in str(git.command)
            args = (
                "--git-dir=repo.git",
                "fetch",
                "--no-tags",
                "--no-recurse-submodules",
                "--",
                url,
                "refs/heads/main",
            )
            if success:
                git.call(*args)
                assert (
                    git.call("--git-dir=repo.git", "show", "FETCH_HEAD:example.txt")
                    == b"synthetic private source"
                )
                assert b"Authorization" not in (root / "repo.git/config").read_bytes()
            else:
                with pytest.raises(TraceProofError):
                    git.call(*args)
        assert 200 in statuses and 401 in statuses
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
