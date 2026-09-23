"""Explicit operator transport settings; never inherit Git or proxy configuration."""

import ssl
from pathlib import Path
from urllib.parse import urlsplit

from veriflow.domain import VeriFlowError


def transport_settings(ca_bundle=None, proxy=None):
    """Validate before acquisition; return pinned CA bytes and a credential-free proxy."""
    ca = None
    if ca_bundle is not None:
        try:
            with Path(ca_bundle).open("rb") as source:
                ca = source.read(1024 * 1024 + 1)
            if not ca or len(ca) > 1024 * 1024:
                raise ValueError
            ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=ca.decode("ascii"))
        except (OSError, ValueError, UnicodeError, ssl.SSLError):
            raise VeriFlowError(
                "CA bundle must be readable PEM certificates, at most 1 MiB"
            ) from None
    if proxy is not None:
        try:
            parsed = urlsplit(proxy)
            valid = (
                len(proxy) <= 2048
                and proxy.isascii()
                and not any(c.isspace() or ord(c) < 32 for c in proxy)
                and not any(c in proxy for c in ("%", "\\"))
                and parsed.scheme in ("http", "https")
                and parsed.hostname
                and parsed.username is None
                and parsed.password is None
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
                and (parsed.port is None or 1 <= parsed.port <= 65535)
            )
            if not valid:
                raise ValueError
        except ValueError:
            raise VeriFlowError(
                "Proxy requires a credential-free HTTP(S) host and optional port"
            ) from None
    return ca, proxy


def configure(git, settings):
    ca, proxy = settings
    if ca is not None:
        # Copy validated bytes into private scratch so mount updates cannot change this fetch.
        path = git.root / "transport-ca.pem"
        path.write_bytes(ca)
        path.chmod(0o600)
        git.command.extend(["-c", f"http.sslCAInfo={path}", "-c", f"http.proxySSLCAInfo={path}"])
    if proxy is not None:
        git.command.extend(["-c", f"http.proxy={proxy}", "-c", "http.proxySSLVerify=true"])
