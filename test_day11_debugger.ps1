$ErrorActionPreference = "Stop"
$pass = 0
$fail = 0

function Check($name, $cond, $extra = "") {
  if ($cond) { Write-Host "  PASS: $name" -ForegroundColor Green; $script:pass++ }
  else       { Write-Host "  FAIL: $name  $extra" -ForegroundColor Red; $script:fail++ }
}

$base = "http://127.0.0.1:8080/api"
$token = (Get-Content token.txt -Raw).Trim()
$h0 = @{ Authorization = "Bearer $token" }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Voxera Day 11 - Debugger Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
$tenantId = $tenants[0].id
$h = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tenantId }

$agents = Invoke-RestMethod -Uri "$base/agents" -Headers $h
$agentId = $agents[0].id

$calls = Invoke-RestMethod -Uri "$base/calls" -Headers $h
if ($calls.Count -eq 0) {
  Write-Host "  creating a call..." -ForegroundColor DarkYellow
  $call = Invoke-RestMethod -Method Post -Uri "$base/calls" -Headers $h -Body (@{
    agent_id = $agentId
  } | ConvertTo-Json)
  $calls = @($call)
}
$callId = $calls[0].id

Write-Host ""
Write-Host "[1] Debug a call" -ForegroundColor Yellow
$rep = Invoke-RestMethod -Method Post -Uri "$base/debug/calls/$callId" -Headers $h -Body "{}"
Check "report id" ($rep.id.Length -gt 0)
Check "report has category" ($rep.category.Length -gt 0)
Check "report has stage" ($rep.stage.Length -gt 0)
Check "report has severity" ($rep.severity.Length -gt 0)
Check "report has root_cause" ($rep.root_cause.Length -gt 0)
Check "report has confidence" ($rep.confidence -ge 0 -and $rep.confidence -le 1)

Write-Host ""
Write-Host "[2] Category is valid" -ForegroundColor Yellow
$validCats = @("STT_FAILURE","LLM_FAILURE","TOOL_FAILURE","TTS_FAILURE","TIMEOUT","VALIDATION_FAILURE","UNKNOWN")
Check "category in valid set" ($validCats -contains $rep.category) "got $($rep.category)"

Write-Host ""
Write-Host "[3] Evidence + recommendation" -ForegroundColor Yellow
Check "evidence is list" ($rep.evidence -is [array])
Check "recommendation is list" ($rep.recommendation -is [array])
Check "recommendation non-empty" ($rep.recommendation.Count -ge 1)

Write-Host ""
Write-Host "[4] Persistence" -ForegroundColor Yellow
$fetched = Invoke-RestMethod -Uri "$base/debug/calls/$callId" -Headers $h
Check "same report returned" ($fetched.id -eq $rep.id)

Write-Host ""
Write-Host "[5] List reports" -ForegroundColor Yellow
$list = Invoke-RestMethod -Uri "$base/debug/reports" -Headers $h
Check "reports list has >= 1" ($list.Count -ge 1)

Write-Host ""
Write-Host "[6] Debug an evaluation result" -ForegroundColor Yellow
$ds = Invoke-RestMethod -Method Post -Uri "$base/evaluations" -Headers $h -Body (@{
  name = "Debug Test $([guid]::NewGuid().ToString('N').Substring(0,6))"
  agent_id = $agentId
} | ConvertTo-Json)
$c1 = Invoke-RestMethod -Method Post -Uri "$base/evaluations/$($ds.id)/cases" -Headers $h -Body (@{
  name = "Impossible"; input_text = "What is 100 * 100?"
  expected_output = "9999999"; expected_tools = @("calculate")
  max_latency_ms = 300000; enabled = $true
} | ConvertTo-Json)
$run = Invoke-RestMethod -Method Post -Uri "$base/evaluations/$($ds.id)/run" -Headers $h -Body "{}"
$results = Invoke-RestMethod -Uri "$base/evaluations/$($ds.id)/runs/$($run.id)/results" -Headers $h
$resId = $results[0].id
$rep2 = Invoke-RestMethod -Method Post -Uri "$base/debug/evaluation-results/$resId" -Headers $h -Body "{}"
Check "eval debug created" ($rep2.id.Length -gt 0)
Check "eval debug has category" ($rep2.category.Length -gt 0)

Write-Host ""
Write-Host "[7] Cross-tenant isolation" -ForegroundColor Yellow
$stamp = [guid]::NewGuid().ToString("N").Substring(0,8)
$otherReg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -Headers @{ "Content-Type" = "application/json" } -Body (@{
  email = "dbg-$stamp@voxera.dev"; password = "password123"; organization_name = "Dbg $stamp"
} | ConvertTo-Json)
$otherToken = $otherReg.access_token
$otherMe = Invoke-RestMethod -Uri "$base/auth/me" -Headers @{ Authorization = "Bearer $otherToken" }
$otherTenants = Invoke-RestMethod -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken" }
if ($otherTenants.Count -eq 0) {
  $ot = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken"; "Content-Type" = "application/json" } -Body (@{
    organization_id = $otherMe.organization_id; name = "Other"; slug = "dbg-$stamp"
  } | ConvertTo-Json)
  $otherTenants = @($ot)
}
$crossBlocked = $false
try {
  Invoke-RestMethod -Uri "$base/debug/calls/$callId" -Headers @{
    Authorization = "Bearer $otherToken"; "X-Tenant-ID" = $otherTenants[0].id
  } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 404) { $crossBlocked = $true }
}
Check "cross-tenant → 404" $crossBlocked

Write-Host ""
Write-Host "[8] Authentication" -ForegroundColor Yellow
$noAuth = $false
try {
  Invoke-RestMethod -Uri "$base/debug/reports" -Headers @{ "X-Tenant-ID" = $tenantId } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) { $noAuth = $true }
}
Check "no auth → 401" $noAuth

$noTenant = $false
try {
  Invoke-RestMethod -Uri "$base/debug/reports" -Headers @{ Authorization = "Bearer $token" } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 422) { $noTenant = $true }
}
Check "no tenant → 422" $noTenant

Write-Host ""
Write-Host "[9] UI asset" -ForegroundColor Yellow
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/js/views/debug.js" -UseBasicParsing
Check "debug.js served" ($r.StatusCode -eq 200)
Check "has DebugPanel" ($r.Content -match "DebugPanel")

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""