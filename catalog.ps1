#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& uv run --project (Join-Path $Root "tools") catalog @args
exit $LASTEXITCODE
