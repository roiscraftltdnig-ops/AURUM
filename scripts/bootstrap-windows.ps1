param(
  [switch]$InstallTools,
  [switch]$PortableValidationTools
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

if ($InstallTools) {
  winget install --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  winget install --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
  winget install --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
}

if ($PortableValidationTools) {
  New-Item -ItemType Directory -Force -Path "tools" | Out-Null
  if (!(Test-Path "tools\python-3.12.8-embed-amd64.zip")) {
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip" -OutFile "tools\python-3.12.8-embed-amd64.zip"
  }
  if (!(Test-Path "tools\python-3.12.8\python.exe")) {
    Expand-Archive -Path "tools\python-3.12.8-embed-amd64.zip" -DestinationPath "tools\python-3.12.8" -Force
  }
  & "tools\python-3.12.8\python.exe" -m compileall backend\app
}

Write-Host ""
Write-Host "Required manual values in .env:"
Write-Host "- OPENAI_API_KEY"
Write-Host "- TELEGRAM_BOT_TOKEN"
Write-Host "- TELEGRAM_WEBHOOK_SECRET"
Write-Host "- SUPABASE_URL"
Write-Host "- SUPABASE_ANON_KEY"
Write-Host "- SUPABASE_SERVICE_ROLE_KEY"
Write-Host "- APP_BASE_URL when deployed to HTTPS"
Write-Host ""
Write-Host "After tools and secrets are ready:"
Write-Host "1. Run supabase/migrations/001_initial_schema.sql in Supabase SQL Editor."
Write-Host "2. Run docker compose up --build"
Write-Host "3. Open http://localhost:3000"
