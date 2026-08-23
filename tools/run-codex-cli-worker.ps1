$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:CODEX_CLI_PROJECT_DIR = $repoRoot

Write-Host "Starting StyleReporter Codex CLI worker for $repoRoot"
python (Join-Path $PSScriptRoot "codex_cli_worker.py")
