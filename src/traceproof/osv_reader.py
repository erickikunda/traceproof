"""Explicit HTTPS reader for OSV archives; no redirects, no proxy or CA inheritance."""

import ssl
import urllib.error
import urllib.request

from traceproof.domain import TraceProofError
from traceproof.git_transport import transport_settings

CHUNK = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # A redirect could leave the allowed host after validation, so refuse it outright.
        raise TraceProofError("OSV source redirected; acquisition requires a direct response")


class OSVReader:
    def __init__(self, *, ca_bundle=None, proxy=None, timeout=300):
        if not 1 <= timeout <= 900:
            raise TraceProofError("OSV reader timeout must be bounded")
        ca, self.proxy = transport_settings(ca_bundle, proxy)
        self.timeout = timeout
        self.context = ssl.create_default_context()
        if ca is not None:
            self.context.load_verify_locations(cadata=ca.decode("ascii"))
        self.context.check_hostname = True
        self.context.verify_mode = ssl.CERT_REQUIRED

    def opener(self):
        handlers = [
            urllib.request.HTTPSHandler(context=self.context),
            NoRedirect(),
            # An empty mapping disables environment proxy discovery.
            urllib.request.ProxyHandler({"https": self.proxy} if self.proxy else {}),
        ]
        return urllib.request.build_opener(*handlers)

    def fetch(self, url, max_bytes):
        request = urllib.request.Request(url, method="GET")
        request.add_header("Accept", "application/zip")
        body = bytearray()
        try:
            with self.opener().open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise TraceProofError("OSV source did not return a complete response")
                while block := response.read(CHUNK):
                    body.extend(block)
                    if len(body) > max_bytes:
                        raise TraceProofError("OSV archive exceeds the accepted byte limit")
        except TraceProofError:
            raise
        except (urllib.error.URLError, ssl.SSLError, OSError, ValueError) as exc:
            raise TraceProofError(f"OSV archive fetch failed ({type(exc).__name__})") from exc
        return bytes(body)
