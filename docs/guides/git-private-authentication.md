# Private HTTPS Git acquisition

Slice 117 adds --credential-file to acquire-git and acquire-git-csv. It supports HTTP Basic
credentials, including a server-supported token used as the password. It does not implement
SSH, browser/SSO login, OAuth token refresh, client certificates or authenticated proxies.

Mount an operator-managed JSON secret outside source/input/output directories:

```json
{"url":"https://git.example.invalid/team/repo.git","username":"READER_USERNAME","password":"TOKEN_PLACEHOLDER"}
```

The URL must exactly match the requested repository URL, which must separately pass the
HTTPS host allowlist. One credential file authorizes one repository URL; mixed-repository
batches fail mismatching rows rather than sending credentials to other repositories.
The file is bounded to 16 KiB. Empty fields, control characters and colon-bearing usernames
are rejected. Use least-privilege read credentials and protect the mount with operator-only
access; do not put actual credentials in shell commands, CSV metadata or the repository.
Kubernetes Secret projection symlinks are supported. Keep the file stable throughout a batch;
each row reads it anew, permitting operator rotation between separate acquisitions.

```sh
veriflow acquire-git-csv /staging/repositories.csv /staging/new-batch \
  --allowed-host git.example.invalid \
  --credential-file /secrets/git-reader.json \
  --ca-bundle /config/corporate-ca.pem
```

Credentials are encoded as an Authorization header in the fetch child process environment,
not command arguments, Git repository config, archives or receipts. Encoding is not encryption:
the environment and process memory are sensitive to same-user/privileged inspection. Keep
acquisition isolated from repository execution, debugging dumps and untrusted processes.
Redirects remain disabled; the header is scoped to the exact configured HTTPS repository URL.
Git stderr is suppressed and errors are sanitized. Other Git operations do not receive the
credential environment. The offline scanner needs no secret mount or provider access.

Validation uses a local synthetic HTTPS Git fixture: correct CA/credentials fetch source;
wrong credentials and untrusted CA fail. The fixture uses a random local port and Git's HTTP
static-object transport, not a bank server or the public acquire command's port-443 contract.
This does not qualify enterprise SSO, smart-HTTP shallow acquisition, proxy behavior or OCP.
Slice 118 refreshes the image and validates port-443 smart-HTTP shallow acquisition, CSV acquisition and an HTTP CONNECT proxy locally. Bank infrastructure and HTTPS-proxy acceptance remain pending.
