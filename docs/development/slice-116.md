# Slice 116 — Explicit Git CA and proxy configuration

Single and CSV Git acquisition accept --ca-bundle and --proxy. These are trusted operator
options, never CSV fields. CA input is bounded to 1 MiB and parsed as PEM certificates;
validated bytes are copied into private per-acquisition scratch. Credential-bearing,
malformed and non-HTTP(S) proxy URLs are rejected with sanitized errors. TLS verification,
no redirects, disabled credential helpers and the minimal Git environment remain intact.
An HTTPS proxy uses the supplied CA bundle for proxy TLS too.

The CA path is validated at batch admission and read again for each row. Operators must
keep configuration mounts stable throughout the batch; each individual acquisition pins
its validated bytes. No new receipt fields, database migration or model calls. Proxy and
CA configuration are not stored in source provenance. Proxy hostname/path configuration
can be visible in local process arguments; no proxy credentials are accepted.

Validation: existing acquisition/batch tests plus certificate parsing/copying, invalid
proxy rejection, pre-output failure and inherited-environment isolation. Native Git
--version runs with the settings, but this is not end-to-end corporate proxy/TLS acceptance.
Private Git and authenticated proxies remain unsupported. Existing container image digests
are unchanged; rebuild the acquisition wheel/image before using these options in a container.

Next: bounded private HTTPS authentication and local transport integration validation,
then refresh the acquisition image. Bank infrastructure and OCP acceptance remain deferred.
