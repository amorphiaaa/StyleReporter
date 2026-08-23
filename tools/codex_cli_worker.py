"""Local HTTP companion that turns report requests into `codex exec` runs.

The worker intentionally stays outside Docker because the host Codex CLI owns
the user's saved authentication session. It is for local development only.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
RUN_LOCK = Lock()


class WorkerError(RuntimeError):
    """A safe, user-facing worker error."""


class CodexCliRunner:
    def __init__(
        self,
        *,
        project_dir: Path,
        timeout_seconds: float,
        asset_root: Path | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.timeout_seconds = timeout_seconds
        self.asset_root = (asset_root or project_dir / "var" / "assets").resolve()

    def run(
        self,
        *,
        prompt: str,
        output_schema: dict[str, Any],
        model: str | None,
        image_paths: Sequence[str] = (),
    ) -> dict[str, Any]:
        executable = shutil.which(os.getenv("CODEX_CLI_EXECUTABLE", "codex"))
        if not executable:
            raise WorkerError(
                "Codex CLI was not found on PATH. Install it and verify `codex --version`."
            )
        if not self.project_dir.is_dir():
            raise WorkerError(f"Codex CLI project directory does not exist: {self.project_dir}")
        resolved_image_paths = _resolve_image_paths(image_paths, self.asset_root)

        with tempfile.TemporaryDirectory(prefix="stylereporter-codex-") as temp_dir:
            temp_path = Path(temp_dir)
            schema_path = temp_path / "style-report.schema.json"
            output_path = temp_path / "style-report.json"
            schema_path.write_text(json.dumps(output_schema), encoding="utf-8")

            command = [
                executable,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "--cd",
                str(self.project_dir),
            ]
            for image_path in resolved_image_paths:
                command.extend(["--image", str(image_path)])
            if model:
                command.extend(["--model", model])
            command.append("-")

            try:
                completed = subprocess.run(
                    command,
                    input=prompt.encode("utf-8"),
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    cwd=self.project_dir,
                )
            except subprocess.TimeoutExpired as exc:
                raise WorkerError(
                    f"Codex CLI timed out after {self.timeout_seconds:.0f} seconds."
                ) from exc
            except OSError as exc:
                raise WorkerError(f"Could not start Codex CLI: {exc}") from exc

            if completed.returncode != 0:
                detail = _decode_process_output(completed.stderr or completed.stdout).strip()
                raise WorkerError(
                    f"Codex CLI exited with code {completed.returncode}: {detail[-1000:]}"
                )

            raw_output = (
                output_path.read_text(encoding="utf-8")
                if output_path.exists()
                else _decode_process_output(completed.stdout)
            )
            try:
                payload = json.loads(raw_output)
            except json.JSONDecodeError as exc:
                raise WorkerError("Codex CLI returned non-JSON output despite the output schema.") from exc
            if not isinstance(payload, dict):
                raise WorkerError("Codex CLI returned a JSON value instead of an object.")
            return payload


def _decode_process_output(value: bytes) -> str:
    """Decode CLI output without allowing a localized Windows code page to leak in."""

    return value.decode("utf-8", errors="replace")


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "StyleReporterCodexWorker/1.0"

    def do_GET(self) -> None:
        if self.path != "/health":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found."})
            return
        self._send_json(
            HTTPStatus.OK,
            {"status": "ok", "service": "stylereporter-codex-cli-worker"},
        )

    def do_POST(self) -> None:
        if self.path != "/v1/style-reports":
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found."})
            return
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Invalid worker token."})
            return
        if not RUN_LOCK.acquire(blocking=False):
            self._send_json(HTTPStatus.CONFLICT, {"detail": "Another Codex CLI run is in progress."})
            return

        try:
            payload = self._read_json()
            prompt = payload.get("prompt")
            output_schema = payload.get("output_schema")
            if not isinstance(prompt, str) or not prompt.strip():
                raise WorkerError("Request field 'prompt' must be a non-empty string.")
            if not isinstance(output_schema, dict):
                raise WorkerError("Request field 'output_schema' must be a JSON object.")

            project_dir = Path(os.getenv("CODEX_CLI_PROJECT_DIR", str(PROJECT_DIR))).resolve()
            runner = CodexCliRunner(
                project_dir=project_dir,
                timeout_seconds=float(os.getenv("CODEX_CLI_TIMEOUT_SECONDS", "600")),
                asset_root=Path(
                    os.getenv("CODEX_CLI_ASSET_ROOT", str(project_dir / "var" / "assets"))
                ),
            )
            report = runner.run(
                prompt=prompt,
                output_schema=output_schema,
                model=payload.get("model") if isinstance(payload.get("model"), str) else None,
                image_paths=_validated_image_paths(payload.get("image_paths")),
            )
            self._send_json(HTTPStatus.OK, {"report": report})
        except (ValueError, WorkerError) as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"detail": str(exc)})
        finally:
            RUN_LOCK.release()

    def log_message(self, format: str, *args: object) -> None:
        # Do not log request bodies: they contain questionnaire data.
        super().log_message(format, *args)

    def _authorized(self) -> bool:
        expected = os.getenv("CODEX_CLI_RUNNER_TOKEN", "")
        if not expected:
            return True
        actual = self.headers.get("X-Codex-Runner-Token", "")
        return hmac.compare_digest(actual, expected)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise WorkerError("Request body is empty or too large.")
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as exc:
            raise WorkerError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise WorkerError("Request body must be a JSON object.")
        return payload

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _validated_image_paths(value: object) -> Sequence[str]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkerError("Request field 'image_paths' must be a list of strings.")
    return value


def _resolve_image_paths(image_paths: Sequence[str], asset_root: Path) -> list[Path]:
    if len(image_paths) > 20:
        raise WorkerError("A report may attach at most 20 images.")

    root = asset_root.resolve()
    resolved: list[Path] = []
    for image_path in image_paths:
        candidate_path = Path(image_path)
        if candidate_path.is_absolute():
            raise WorkerError("Image paths must be relative to CODEX_CLI_ASSET_ROOT.")
        candidate = (root / candidate_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise WorkerError("Image path escapes CODEX_CLI_ASSET_ROOT.") from exc
        if candidate.suffix.lower() not in {".gif", ".heic", ".jpg", ".png", ".webp"}:
            raise WorkerError("Image path has an unsupported file extension.")
        if not candidate.is_file() or candidate.stat().st_size <= 0:
            raise WorkerError(f"Image file was not found: {image_path}")
        resolved.append(candidate)
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("CODEX_CLI_RUNNER_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CODEX_CLI_RUNNER_PORT", "8787")),
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), WorkerHandler)
    print(f"StyleReporter Codex CLI worker listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
