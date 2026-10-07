$ErrorActionPreference = "Stop"
$pass = 0
$fail = 0

function Check($name, $cond, $extra = "") {
  if ($cond) {
    Write-Host "  PASS: $name" -ForegroundColor Green
    $script:pass++
  } else {
    Write-Host "  FAIL: $name  $extra" -ForegroundColor Red
    $script:fail++
  }
}

$base = "http://127.0.0.1:8080/api"
$token = (Get-Content token.txt -Raw).Trim()
$h0 = @{ Authorization = "Bearer $token" }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Voxera Day 9 - Trace Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
$tenantId = $tenants[0].id
$h = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tenantId }

# Ensure at least one call exists
$calls = Invoke-RestMethod -Uri "$base/calls" -Headers $h
if ($calls.Count -eq 0) {
  $agents = Invoke-RestMethod -Uri "$base/agents" -Headers $h
  if ($agents.Count -eq 0) {
    Write-Host "No agent to create a call with. Run day8b_test.ps1 first." -ForegroundColor Red
    exit 1
  }
  $agentId = $agents[0].id
  $call = Invoke-RestMethod -Method Post -Uri "$base/calls" -Headers $h -Body (@{
    agent_id = $agentId
  } | ConvertTo-Json)
  $msg = Invoke-RestMethod -Method Post -Uri "$base/calls/$($call.id)/messages" -Headers $h -Body (@{
    content = "What time is it?"
  } | ConvertTo-Json)
  Invoke-RestMethod -Method Post -Uri "$base/calls/$($call.id)/end" -Headers $h | Out-Null
  $calls = Invoke-RestMethod -Uri "$base/calls" -Headers $h
}
$callId = $calls[0].id

Write-Host ""
Write-Host "[1] List calls" -ForegroundColor Yellow
Check "GET /calls returns 200" ($calls.Count -ge 1)
Check "Call has agent_name" ($null -ne $calls[0].agent_name)
Check "Call has duration_ms" ($calls[0].duration_ms -ge 0)
Check "Call has message_count" ($calls[0].message_count -ge 1)

Write-Host ""
Write-Host "[2] Call detail" -ForegroundColor Yellow
$detail = Invoke-RestMethod -Uri "$base/calls/$callId" -Headers $h
Check "GET /calls/{id} 200" ($detail.id -eq $callId)
Check "Detail has model_name" ($detail.model_name.Length -gt 0)

Write-Host ""
Write-Host "[3] Messages" -ForegroundColor Yellow
$msgs = Invoke-RestMethod -Uri "$base/calls/$callId/messages" -Headers $h
Check "GET messages 200" ($msgs.Count -ge 1)
Check "First msg has role" ($msgs[0].role.Length -gt 0)

Write-Host ""
Write-Host "[4] Traces" -ForegroundColor Yellow
$trc = Invoke-RestMethod -Uri "$base/calls/$callId/traces" -Headers $h
Write-Host "  trace count: $($trc.Count)"
Check "GET traces 200" ($true)

Write-Host ""
Write-Host "[5] Timeline" -ForegroundColor Yellow
$tl = Invoke-RestMethod -Uri "$base/calls/$callId/timeline" -Headers $h
Check "GET timeline 200" ($tl.Count -ge 2)
$kinds = ($tl | ForEach-Object { $_.kind }) -join ","
Check "Timeline has lifecycle" ($kinds -match "lifecycle")
Check "Timeline has message"   ($kinds -match "message")

Write-Host ""
Write-Host "[6] Authentication" -ForegroundColor Yellow
$noAuth = $false
try {
  Invoke-RestMethod -Uri "$base/calls" -Headers @{ "X-Tenant-ID" = $tenantId } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) { $noAuth = $true }
}
Check "No auth → 401" $noAuth

Write-Host ""
Write-Host "[7] Tenant required" -ForegroundColor Yellow
$noTenant = $false
try {
  Invoke-RestMethod -Uri "$base/calls" -Headers @{ Authorization = "Bearer $token" } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 422) { $noTenant = $true }
}
Check "No tenant → 422" $noTenant

Write-Host ""
Write-Host "[8] Cross-tenant isolation" -ForegroundColor Yellow
$stamp = [guid]::NewGuid().ToString("N").Substring(0,8)
$reg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -Headers @{ "Content-Type" = "application/json" } -Body (@{
  email = "trace-$stamp@voxera.dev"
  password = "password123"
  organization_name = "TraceOrg $stamp"
} | ConvertTo-Json)
$otherToken = $reg.access_token
$otherMe = Invoke-RestMethod -Uri "$base/auth/me" -Headers @{ Authorization = "Bearer $otherToken" }
$otherTenants = Invoke-RestMethod -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken" }
if ($otherTenants.Count -eq 0) {
  $ot = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken"; "Content-Type" = "application/json" } -Body (@{
    organization_id = $otherMe.organization_id
    name = "Other Tenant"
    slug = "other-$stamp"
  } | ConvertTo-Json)
  $otherTenants = @($ot)
}
$crossBlocked = $false
try {
  Invoke-RestMethod -Uri "$base/calls/$callId" -Headers @{
    Authorization = "Bearer $otherToken"
    "X-Tenant-ID" = $otherTenants[0].id
  } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 404) { $crossBlocked = $true }
}
Check "Cross-tenant call → 404" $crossBlocked

Write-Host ""
Write-Host "[9] Timeline contents" -ForegroundColor Yellow
$names = ($tl | ForEach-Object { $_.name }) -join ","
Check "Has CALL_STARTED" ($names -match "CALL_STARTED")
Check "Has MESSAGE" ($names -match "MESSAGE")

Write-Host ""
Write-Host "[10] Latency data" -ForegroundColor Yellow
$lat = Invoke-RestMethod -Uri "$base/calls/$callId/latency" -Headers $h
Check "Latency has total_ms" ($lat.total_ms -ge 0)
Check "Latency has llm_ms"   ($lat.llm_ms -ge 0)
Check "Latency has tools_ms" ($lat.tools_ms -ge 0)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""