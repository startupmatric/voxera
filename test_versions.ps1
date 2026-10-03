$ErrorActionPreference = "Stop"

$token = (Get-Content token.txt -Raw).Trim()
if (-not $token -or $token.Length -lt 20) {
  Write-Host "ERROR: token.txt is empty or too short." -ForegroundColor Red
  exit 1
}
Write-Host "Token length: $($token.Length)" -ForegroundColor Green

$base = "http://127.0.0.1:8080/api"

Write-Host "`n=== /auth/me ===" -ForegroundColor Cyan
$h0 = @{ Authorization = "Bearer $token" }
$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
Write-Host "  Email: $($me.email)  Role: $($me.role)"
$orgId = $me.organization_id

Write-Host "`n=== Tenants ===" -ForegroundColor Cyan
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$orgId" -Headers $h0
if ($tenants.Count -eq 0) {
  $t = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers $h0 -Body (@{
    organization_id = $orgId; name = "Version Test Tenant"; slug = "vt-$(Get-Random)"
  } | ConvertTo-Json)
  $tenants = @($t)
}
$tenantId = $tenants[0].id
Write-Host "  Tenant: $($tenants[0].name)  ($tenantId)"

# All agent-scoped requests need BOTH auth + tenant header
$h = @{
  Authorization = "Bearer $token"
  "Content-Type" = "application/json"
  "X-Tenant-ID" = $tenantId
}

Write-Host "`n=== Create agent ===" -ForegroundColor Cyan
$agent = Invoke-RestMethod -Method Post -Uri "$base/agents" -Headers $h -Body (@{
  tenant_id = $tenantId
  name = "Version Demo $(Get-Random)"
} | ConvertTo-Json)
$agentId = $agent.id
Write-Host "  Agent: $($agent.name)  ($agentId)"
Write-Host "  Initial temperature: $($agent.temperature)"

$versions = Invoke-RestMethod -Uri "$base/agents/$agentId/versions" -Headers $h
Write-Host "`n  Versions after create:" -ForegroundColor Yellow
$versions | Format-Table version, is_active, temperature, model_name -AutoSize

Write-Host "`n=== PATCH agent (should create v2 draft) ===" -ForegroundColor Cyan
Invoke-RestMethod -Method Patch -Uri "$base/agents/$agentId" -Headers $h -Body (@{
  system_prompt = "You are a helpful assistant v2."
  temperature = 0.9
} | ConvertTo-Json) | Out-Null

$versions = Invoke-RestMethod -Uri "$base/agents/$agentId/versions" -Headers $h
Write-Host "  Versions after PATCH:" -ForegroundColor Yellow
$versions | Format-Table version, is_active, temperature -AutoSize

$active = $versions | Where-Object { $_.is_active -eq $true }
Write-Host "  Active version(s): $($active.Count)  ->  should be exactly 1 (v1)" -ForegroundColor Yellow

Write-Host "`n=== Activate v2 ===" -ForegroundColor Cyan
$v2 = $versions | Where-Object { $_.version -eq 2 }
if ($v2) {
  Invoke-RestMethod -Method Post -Uri "$base/agents/$agentId/versions/$($v2.id)/activate" -Headers $h -Body "{}" | Out-Null
  $versions = Invoke-RestMethod -Uri "$base/agents/$agentId/versions" -Headers $h
  Write-Host "  Versions after activating v2:" -ForegroundColor Yellow
  $versions | Format-Table version, is_active, temperature -AutoSize

  $agentAfter = Invoke-RestMethod -Uri "$base/agents/$agentId" -Headers $h
  Write-Host "  Agent temperature now: $($agentAfter.temperature)  ->  should be 0.9" -ForegroundColor Yellow
}

Write-Host "`n=== Rollback to v1 ===" -ForegroundColor Cyan
$v1 = $versions | Where-Object { $_.version -eq 1 }
Invoke-RestMethod -Method Post -Uri "$base/agents/$agentId/versions/$($v1.id)/rollback" -Headers $h -Body "{}" | Out-Null

$agentAfter = Invoke-RestMethod -Uri "$base/agents/$agentId" -Headers $h
Write-Host "  Agent temperature after rollback: $($agentAfter.temperature)  ->  should be 0.7" -ForegroundColor Yellow

$versions = Invoke-RestMethod -Uri "$base/agents/$agentId/versions" -Headers $h
$active = $versions | Where-Object { $_.is_active -eq $true }
Write-Host "  Active version after rollback: v$($active.version)" -ForegroundColor Yellow

Write-Host "`n=== All done ===" -ForegroundColor Green