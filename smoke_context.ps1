# smoke_context.ps1 — verifies namespaced learning prevents cross-talk
# Requires the API running on http://127.0.0.1:8000

$ErrorActionPreference = "Stop"

function Post-Commit($term, $code, $display, $ctx) {
  $payload = @{
    term=$term
    code=$code
    display=$display
    lay_text=$term
    dry_run=$false
    context=$ctx
  } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/commit_selection" -ContentType "application/json" -Body $payload
}

Write-Host "1) Learn 'watery eyes' in pmh.condition context"
$res1 = Post-Commit "watery eyes" "231834007" "Epiphora" "pmh.condition"
if (-not $res1.ok) { Throw "Learn #1 failed" }
Write-Host "   OK"

Write-Host "2) Learn 'watery eyes' in lab.test context (different concept on purpose)"
$res2 = Post-Commit "watery eyes" "38341003" "Hypertension" "lab.test"
if (-not $res2.ok) { Throw "Learn #2 failed" }
Write-Host "   OK"

Write-Host "3) Verify distinct keys were created (by reading layman_learned.json)"
$path = "data/layman_learned.json"
if (-not (Test-Path $path)) { Throw "Missing $path" }
$json = Get-Content $path -Raw | ConvertFrom-Json
if (-not $json."pmh.condition::watery eyes") { Throw "Missing pmh.condition::watery eyes" }
if (-not $json."lab.test::watery eyes") { Throw "Missing lab.test::watery eyes" }
Write-Host "   OK"

Write-Host "`nContext smoke passed."
