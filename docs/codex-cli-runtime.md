# Local Codex CLI report runtime

StyleReporter can generate a real style-language report without an
`OPENAI_API_KEY`. The backend sends the normalized questionnaire context to a
small host-side HTTP worker, and that worker invokes the locally installed
`codex exec` command.

## Why there is a worker

The backend normally runs in Docker, while the user's Codex CLI installation
and saved login session live on Windows. The worker keeps those responsibilities
separate:

```text
React -> FastAPI/PostgreSQL -> HTTP -> codex_cli_worker.py -> codex exec
```

The worker uses `--sandbox read-only`, `--ephemeral`, and `--output-schema`.
It never receives a request to edit the repository. Questionnaire data is sent
to Codex as the prompt, and verified local image files are attached with
`codex exec --image` when the submission manifest contains downloaded assets.
Treat the worker as a local development service.

## Start locally

In PowerShell, authenticate Codex once if needed:

```powershell
codex login
codex --version
```

Start the worker in a separate terminal:

```powershell
.\tools\run-codex-cli-worker.ps1
```

The worker listens on `http://localhost:8787`. Verify only the worker process
first:

```powershell
Invoke-RestMethod http://localhost:8787/health
```

The worker resolves relative image paths against `CODEX_CLI_ASSET_ROOT`, which
defaults to `var/assets` in the repository. This must point to the same host
folder mounted into the backend container. The backend Compose volume already
maps `./var/assets` to `/var/lib/stylereporter/assets`.

Then start the regular stack:

```powershell
docker compose up --build
```

Docker Desktop resolves `host.docker.internal` to the Windows host. The
Compose backend uses `CODEX_CLI_RUNNER_URL=http://host.docker.internal:8787`.
If the backend is started directly on Windows instead of Docker, use
`CODEX_CLI_RUNNER_URL=http://127.0.0.1:8787`.

## Optional local token

The worker is intended for local use only. To add a shared token, set the same
value in the host worker and backend environment:

```powershell
$env:CODEX_CLI_RUNNER_TOKEN = "local-development-token"
```

The backend sends it as `X-Codex-Runner-Token`. Never commit the token.

## API usage

Use the client detail screen's `Codex CLI (local)` runtime, or send:

```json
{
  "submission_id": "<saved-submission-id>",
  "runtime": "codex_cli"
}
```

The result is persisted as `codex-cli-v1`. If the worker is stopped, the API
persists a failed report run and returns `502`; no questionnaire data is lost.

## Boundaries

- This path does not use `OPENAI_API_KEY`.
- The worker reuses the saved local Codex CLI authentication session.
- Only manifest entries with `status: "downloaded"` and an existing supported
  image file are attached to a run.
- `ASSET_DOWNLOAD_ENABLED` is false by default; enable it before a sync when
  Google Drive files should be copied into the local workspace.
- The worker is not a production queue, scheduler, or public API.
- Generated reports still require methodology review and human approval before
  being delivered to a client.
- Unit tests use mocked HTTP transport; they never invoke Codex CLI.
