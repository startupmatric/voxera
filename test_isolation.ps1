# test_isolation.ps1 — Voxera Day 2 tenant isolation proof

$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"

# Unique suffix so re-runs don't collide on unique slugs
$stamp = Get-Date -Format "yyyyMMddHHmmss"

function Post-Json($path, $obj) {
    $body = $obj | ConvertTo-Json -Compress
    return Invoke-RestMethod -Method Post -Uri "$base$path" `
        -ContentType "application/json" -Body $body
}

function Get-With-Tenant($path, $tenantId) {
    return Invoke-RestMethod -Uri "$base$path" `
        -Headers @{ "X-Tenant-ID" = $tenantId }
}

# --- Org A + Tenant A + Agent A ---
$orgA    = Post-Json "/organizations" @{ name = "Acme Motors $stamp"; slug = "acme-$stamp" }
$tenantA = Post-Json "/tenants"       @{ organization_id = $orgA.id; name = "Bangalore Support"; slug = "blr-$stamp" }
$agentA  = Post-Json "/agents"        @{ tenant_id = $tenantA.id; name = "Support Agent A" }

# --- Org B + Tenant B + Agent B ---
$orgB    = Post-Json "/organizations" @{ name = "Beta Corp $stamp"; slug = "beta-$stamp" }
$tenantB = Post-Json "/tenants"       @{ organization_id = $orgB.id; name = "Beta Support"; slug = "beta-$stamp" }
$agentB  = Post-Json "/agents"        @{ tenant_id = $tenantB.id; name = "Support Agent B" }

Write-Host ""
Write-Host "=== Created ===" -ForegroundColor Cyan
Write-Host "ORG_A    : $($orgA.id)"
Write-Host "TENANT_A : $($tenantA.id)"
Write-Host "AGENT_A  : $($agentA.id)"
Write-Host "ORG_B    : $($orgB.id)"
Write-Host "TENANT_B : $($tenantB.id)"
Write-Host "AGENT_B  : $($agentB.id)"
Write-Host ""

# === TEST 1: Same tenant → 200 with correct agent ===
Write-Host "TEST 1: Tenant A fetches its own Agent A (expect 200 + name)" -ForegroundColor Yellow
$r = Get-With-Tenant "/agents/$($agentA.id)" $tenantA.id
Write-Host "  -> HTTP 200, name = '$($r.name)'" -ForegroundColor Green
Write-Host ""

# === TEST 2: Cross tenant → 404 ===
Write-Host "TEST 2: Tenant A tries to access Agent B (must 404)" -ForegroundColor Yellow
try {
    Get-With-Tenant "/agents/$($agentB.id)" $tenantA.id | Out-Null
    Write-Host "  FAIL: got 200, isolation broken!" -ForegroundColor Red
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $detail = $reader.ReadToEnd()
    Write-Host "  -> HTTP $code : $detail" -ForegroundColor Green
}
Write-Host ""

# === TEST 3: List agents → only tenant A's ===
Write-Host "TEST 3: Tenant A lists agents (must show only its own)" -ForegroundColor Yellow
$list = Get-With-Tenant "/agents" $tenantA.id
Write-Host "  Count: $($list.Count)"
foreach ($a in $list) { Write-Host "    - $($a.name)" }
$names = $list | ForEach-Object { $_.name }
if (($names -contains "Support Agent A") -and -not ($names -contains "Support Agent B")) {
    Write-Host "  OK: only Tenant A's agents shown" -ForegroundColor Green
} else {
    Write-Host "  FAIL: unexpected list contents" -ForegroundColor Red
}
Write-Host ""

# === TEST 4: No header → 422 ===
Write-Host "TEST 4: No X-Tenant-ID header (must 422)" -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "$base/agents" | Out-Null
    Write-Host "  FAIL: should have rejected" -ForegroundColor Red
} catch {
    Write-Host "  -> HTTP $($_.Exception.Response.StatusCode.value__) (expected 422)" -ForegroundColor Green
}
Write-Host ""

Write-Host "=== Isolation test complete ===" -ForegroundColor Cyan