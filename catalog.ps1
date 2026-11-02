#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& uv run --directory (Join-Path $Root "tools") catalog @args
exit $LASTEXITCODE
