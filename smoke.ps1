$ErrorActionPreference = 'Stop'

function Check { param($cond,$msg) if (-not $cond) { throw "SMOKE FAIL: $msg" } else { Write-Host "OK - $msg" } }

# Health
$h = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/healthz'
Check ($h.ok -eq $true) 'Health OK'

# Heart attack should expose MI cluster
$r = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/lookup?q=heart%20attack&domain=auto&include_technical=true'
$first = $r.results[0]
$codes = @($first.practitioner_options.snomed | ForEach-Object { $_.code })
Check ($codes -contains '22298006') 'MI present'
Check ($codes -contains '57054005') 'Acute MI present'
Check ($codes -contains '401303003') 'STEMI present'
Check ($codes -contains '401314000') 'NSTEMI present'

# Commit MI
$payload = @{ term='heart attack'; code='22298006'; display='Myocardial infarction'; lay_text='heart attack' } | ConvertTo-Json
$c = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/commit_selection' -Method Post -ContentType 'application/json' -Body $payload
Check ($c.ok -eq $true) 'Commit MI'

# Watery eyes -> Epiphora
$payload2 = @{ term='watery eyes'; code='231834007'; display='Epiphora'; lay_text='watery eyes' } | ConvertTo-Json
$c2 = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/commit_selection' -Method Post -ContentType 'application/json' -Body $payload2
Check ($c2.ok -eq $true) 'Commit Epiphora'

$r2 = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/lookup?q=watery%20eyes&domain=auto&include_technical=true'
Check ($r2.results[0].patient_view -match 'Epiphora') 'Patient view shows Epiphora'

Write-Host ''
Write-Host 'ALL GREEN'
