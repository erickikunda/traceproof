import subprocess

import pytest

from veriflow.domain import VeriFlowError
from veriflow.git_acquisition import Git, acquire
from veriflow.git_transport import configure, transport_settings


@pytest.mark.parametrize(
    "proxy",
    [
        "http://user:secret@proxy.invalid",
        "http://proxy.invalid/path",
        "socks5://proxy.invalid",
        "https://proxy.invalid?token=secret",
        "http://proxy.invalid:99999",
        "http://proxy.invalid\n",
    ],
)
def test_invalid_proxy_is_sanitized(proxy):
    with pytest.raises(VeriFlowError) as error:
        transport_settings(proxy=proxy)
    assert "secret" not in str(error.value)
    assert proxy not in str(error.value)


def test_invalid_ca_fails_before_output(tmp_path):
    ca = tmp_path / "bad.pem"
    ca.write_text("not a certificate")
    with pytest.raises(VeriFlowError, match="CA bundle"):
        acquire(
            "https://example.invalid/a",
            "refs/heads/main",
            ["example.invalid"],
            tmp_path / "out",
            "repo",
            "team",
            "public",
            ca_bundle=ca,
        )
    assert not (tmp_path / "out").exists()


def test_ca_is_pinned_and_inherited_settings_stay_disabled(tmp_path, monkeypatch):
    cert = tmp_path / "cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(tmp_path / "key.pem"),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=synthetic-test",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    settings = transport_settings(cert, "https://proxy.invalid:8443")
    original = cert.read_bytes()
    cert.write_text("changed after validation")
    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@untrusted.invalid")
    monkeypatch.setenv("GIT_SSL_NO_VERIFY", "1")
    root = tmp_path / "scratch"
    root.mkdir()
    git = Git(root, 10)
    configure(git, settings)
    assert (root / "transport-ca.pem").read_bytes() == original
    assert "HTTPS_PROXY" not in git.env and "GIT_SSL_NO_VERIFY" not in git.env
    assert "http.sslVerify=true" in git.command
    assert "http.proxySSLVerify=true" in git.command
    assert "http.proxy=https://proxy.invalid:8443" in git.command
    assert b"git version" in git.call("--version")


def test_no_configuration_keeps_default_transport(tmp_path):
    git = Git(tmp_path, 10)
    original = git.command.copy()
    configure(git, transport_settings())
    assert git.command == original
