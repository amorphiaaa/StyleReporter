import json
from pathlib import Path

from tools.codex_cli_worker import CodexCliRunner, _decode_process_output


def test_decode_process_output_preserves_utf8_text() -> None:
    text = "\u041f\u0440\u0438\u0432\u0435\u0442, \u0441\u0442\u0438\u043b\u044c \u2728"
    assert _decode_process_output(text.encode()) == text


def test_decode_process_output_replaces_invalid_bytes() -> None:
    assert _decode_process_output(b"prefix\x80suffix") == "prefix\ufffdsuffix"


def test_codex_runner_writes_prompt_as_utf8_bytes(monkeypatch) -> None:
    prompt = "\u041f\u0440\u0438\u0432\u0435\u0442, \u0441\u0442\u0438\u043b\u044c \u2728"

    class Completed:
        returncode = 0
        stdout = b""
        stderr = b""

    def fake_run(command, *, input, **kwargs):
        assert input == prompt.encode()
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
        return Completed()

    monkeypatch.setattr("tools.codex_cli_worker.shutil.which", lambda _: "codex")
    monkeypatch.setattr("tools.codex_cli_worker.subprocess.run", fake_run)

    result = CodexCliRunner(project_dir=Path.cwd(), timeout_seconds=1).run(
        prompt=prompt,
        output_schema={"type": "object"},
        model=None,
    )

    assert result == {"ok": True}


def test_codex_runner_attaches_verified_images(monkeypatch, tmp_path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    asset_root = tmp_path / "assets"
    image_path = asset_root / "clients" / "client-1" / "submission-1" / "01.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"synthetic-image")
    captured_command = []

    class Completed:
        returncode = 0
        stdout = b""
        stderr = b""

    def fake_run(command, *, input, **kwargs):
        captured_command.extend(command)
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
        return Completed()

    monkeypatch.setattr("tools.codex_cli_worker.shutil.which", lambda _: "codex")
    monkeypatch.setattr("tools.codex_cli_worker.subprocess.run", fake_run)

    result = CodexCliRunner(
        project_dir=project_dir,
        asset_root=asset_root,
        timeout_seconds=1,
    ).run(
        prompt="prompt",
        output_schema={"type": "object"},
        model=None,
        image_paths=["clients/client-1/submission-1/01.jpg"],
    )

    assert result == {"ok": True}
    image_flag_index = captured_command.index("--image")
    assert Path(captured_command[image_flag_index + 1]) == image_path.resolve()
