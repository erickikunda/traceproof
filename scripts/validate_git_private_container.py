"""Synthetic loopback smart-HTTP acceptance; run inside the acquisition image."""

import base64
import csv
import json
import os
import select
import socket
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def main():
    root = Path("/work/private-fixture")
    root.mkdir()

    def run(*args):
        return subprocess.run(args, check=True, capture_output=True).stdout

    source = root / "source"
    run("git", "init", "-b", "main", str(source))
    (source / "example.txt").write_text("synthetic private source\n")
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
    run("git", "clone", "--bare", str(source), str(root / "repo.git"))
    cert, key = root / "ca.pem", root / "key.pem"
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
    backend = run("git", "--exec-path").decode().strip() + "/git-http-backend"
    expected = "Basic " + base64.b64encode(b"fixture:synthetic-token").decode()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def handle_git(self):
            if self.headers.get("Authorization") != expected:
                requests.append("unauthorized")
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
                self.end_headers()
                return
            requests.append("authorized")
            parsed = urlsplit(self.path)
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            result = subprocess.run(
                [backend],
                input=body,
                capture_output=True,
                check=True,
                env={
                    "PATH": os.defpath,
                    "GIT_PROJECT_ROOT": str(root),
                    "GIT_HTTP_EXPORT_ALL": "1",
                    "PATH_INFO": parsed.path,
                    "QUERY_STRING": parsed.query,
                    "REQUEST_METHOD": self.command,
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": str(len(body)),
                    "REMOTE_USER": "fixture",
                },
            )
            headers, payload = result.stdout.split(b"\r\n\r\n", 1)
            self.send_response(200)
            for line in headers.decode().split("\r\n"):
                name, value = line.split(":", 1)
                self.send_header(name, value.strip())
            self.end_headers()
            self.wfile.write(payload)

        do_GET = handle_git
        do_POST = handle_git

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 443), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    tunnels = []

    class Proxy(BaseHTTPRequestHandler):
        def do_CONNECT(self):
            if self.path != "localhost:443":
                self.send_error(403)
                return
            tunnels.append(self.path)
            with socket.create_connection(("127.0.0.1", 443), timeout=10) as upstream:
                self.send_response(200)
                self.end_headers()
                for _ in range(1000):
                    ready, _, _ = select.select([self.connection, upstream], [], [], 10)
                    if not ready:
                        return
                    for source_socket in ready:
                        data = source_socket.recv(65536)
                        if not data:
                            return
                        (upstream if source_socket is self.connection else self.connection).sendall(
                            data
                        )

        def log_message(self, *args):
            pass

    proxy = ThreadingHTTPServer(("127.0.0.1", 8080), Proxy)
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    url = "https://localhost/repo.git"
    secret = root / "reader.json"
    results = []
    try:
        for name, password, trust, credential_url, expected_code in [
            ("valid", "synthetic-token", True, url, 0),
            ("wrong-password", "wrong-token", True, url, 1),
            ("untrusted-ca", "synthetic-token", False, url, 1),
            ("wrong-repository", "synthetic-token", True, url + "-other", 1),
        ]:
            secret.write_text(
                json.dumps(dict(url=credential_url, username="fixture", password=password))
            )
            secret.chmod(0o600)
            command = [
                "veriflow",
                "acquire-git",
                url,
                "refs/heads/main",
                str(root / name),
                "fixture",
                "poc",
                "synthetic",
                "--allowed-host",
                "localhost",
                "--credential-file",
                str(secret),
            ]
            if trust:
                command += ["--ca-bundle", str(cert)]
            result = subprocess.run(command, capture_output=True, timeout=30)
            assert result.returncode == expected_code, (name, result.stderr.decode())
            assert b"synthetic-token" not in result.stdout + result.stderr
            assert expected.encode() not in result.stdout + result.stderr
            results.append(dict(case=name, exit_code=result.returncode))
        receipt = json.loads((root / "valid/acquisition.json").read_text())
        assert receipt["state"] == "acquired" and receipt["model_calls"] == 0
        assert len(receipt["resolved_commit"]) == 40
        for artifact in (root / "valid").rglob("*"):
            if artifact.is_file():
                assert b"synthetic-token" not in artifact.read_bytes()
                assert expected.encode() not in artifact.read_bytes()
        manifest = root / "repositories.csv"
        with manifest.open("w") as target:
            writer = csv.writer(target)
            writer.writerow(["repo_id", "url", "revision", "owner", "classification"])
            writer.writerow(["fixture", url, "refs/heads/main", "poc", "synthetic"])
        secret.write_text(json.dumps(dict(url=url, username="fixture", password="synthetic-token")))
        run(
            "veriflow",
            "acquire-git-csv",
            str(manifest),
            str(root / "batch"),
            "--allowed-host",
            "localhost",
            "--credential-file",
            str(secret),
            "--ca-bundle",
            str(cert),
        )
        assert (
            json.loads((root / "batch/acquisition-batch.json").read_text())["state"] == "acquired"
        )
        run(
            "veriflow",
            "acquire-git",
            url,
            "refs/heads/main",
            str(root / "proxied"),
            "fixture",
            "poc",
            "synthetic",
            "--allowed-host",
            "localhost",
            "--credential-file",
            str(secret),
            "--ca-bundle",
            str(cert),
            "--proxy",
            "http://127.0.0.1:8080",
        )
        assert tunnels, "Explicit proxy was not used"
        print(
            json.dumps(
                dict(
                    cases=results,
                    batch="acquired",
                    smart_http=True,
                    proxy_connects=len(tunnels),
                    model_calls=0,
                    ocp_qualified=False,
                    uid=os.getuid(),
                    authorized_requests=requests.count("authorized"),
                    rejected_requests=requests.count("unauthorized"),
                )
            )
        )
    finally:
        proxy.shutdown()
        proxy.server_close()
        proxy_thread.join()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
