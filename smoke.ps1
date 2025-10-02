# smoke.ps1 — basic health + lookup + learn happy path
# Requires the API running on http://127.0.0.1:8000

$ErrorActionPreference = "Stop"
function Assert-JsonOk($json) {
  if (-not $json.ok) { Throw "Expected ok=true, got: $($json | ConvertTo-Json -Depth 6)" }
}

Write-Host "1) /healthz"
$health = Invoke-RestMethod "http://127.0.0.1:8000/healthz"
Assert-JsonOk $health
Write-Host "   OK"

Write-Host "2) /lookup heart attack"
$lookup = Invoke-RestMethod "http://127.0.0.1:8000/lookup?query=heart%20attack&domain=auto&include_technical=true&top_k=5&score_cutoff=70&tech_top_k=8&tech_score_cutoff=60"
Assert-JsonOk $lookup
if ($lookup.results[0].snomed -ne "22298006") { Throw "SNOMED mismatch for heart attack" }
Write-Host "   OK"

Write-Host "3) /lookup hemoglobin (canonical LOINC)"
$lookup2 = Invoke-RestMethod "http://127.0.0.1:8000/lookup?query=hemoglobin"
Assert-JsonOk $lookup2
if ($lookup2.results[0].loinc -ne "718-7") { Throw "LOINC mismatch for hemoglobin" }
Write-Host "   OK"

Write-Host "4) /api/commit_selection learn heart attack (global)"
$payload = @{
  term="heart attack"
  code="22298006"
  display="Myocardial infarction"
  lay_text="heart attack"
  dry_run=$false
  context=$null
} | ConvertTo-Json
$res = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/commit_selection" -ContentType "application/json" -Body $payload
if (-not $res.ok) { Throw "commit_selection failed" }
Write-Host "   OK"

Write-Host "`nAll smokes passed."
