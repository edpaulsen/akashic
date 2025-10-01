$ErrorActionPreference = 'Stop'
function Check { param($cond,$msg) if (-not $cond) { throw "SMOKE FAIL: $msg" } else { Write-Host "OK - $msg" } }

# LOINC-only: Hemoglobin
$r1 = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/lookup?q=hemoglobin&domain=loinc&include_technical=true'
Check ($r1.results.Count -ge 1) 'Hemoglobin returns at least one result'
Check ($r1.results[0].loinc_code -ne $null) 'Hemoglobin returns loinc_code'
Check ($r1.results[0].patient_view -match 'Hemoglobin') 'Patient view is populated for Hemoglobin'

# SNOMED-only: heart attack
$r2 = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/lookup?q=heart%20attack&domain=snomed&include_technical=true'
$codes = @($r2.results[0].practitioner_options.snomed | ForEach-Object { $_.code })
Check ($codes -contains '22298006') 'MI present (SNOMED-only route)'
