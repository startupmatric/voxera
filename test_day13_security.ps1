$ErrorActionPreference = "Continue"
$pass = 0
$fail = 0
function Check($name, $cond, $extra = "") {
  if ($cond) { Write-Host "  PASS: $name" -ForegroundColor Green; $script:pass++ }
  else       { Write-Host "  FAIL: $name  $extra" -ForegroundColor Red; $script:fail++ }
}

$base = "http://127.0.0.1:8080/api"
$tokenA = (Get-Content token.txt -Raw).Trim()

Write-Host ""
Write-Host "=== Day 13 Security Audit ===" -ForegroundColor Cyan

# --- Pre-flight: verify the token is valid
if (-not $tokenA -or $tokenA.Length -lt 100) {
  Write-Host "  ABORT: token.txt is empty or too short. Re-login and re-download the token." -ForegroundColor Red
  exit 1
}

$hA = @{ Authorization = "Bearer $tokenA" }
try {
  $meA = Invoke-RestMethod -Uri "$base/auth/me" -Headers $hA
  Write-Host "  Auth OK: $($meA.email)" -ForegroundColor Green
} catch {
  Write-Host "  ABORT: token is invalid or expired. Re-login and re-download token.txt." -ForegroundColor Red
  exit 1
}

# --- Tenant A setup
$tA = (Invoke-RestMethod -Uri "$base/tenants?organization_id=$($meA.organization_id)" -Headers $hA)[0]
$hAT = @{ Authorization = "Bearer $tokenA"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tA.id }

$agentA = (Invoke-RestMethod -Uri "$base/agents" -Headers $hAT)[0]
$callA  = (Invoke-RestMethod -Uri "$base/calls" -Headers $hAT)[0]
$dsA    = (Invoke-RestMethod -Uri "$base/evaluations" -Headers $hAT)[0]

# --- Tenant B setup
$stamp = [guid]::NewGuid().ToString("N").Substring(0,8)
$regB = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -Headers @{ "Content-Type" = "application/json" } -Body (@{
  email = "sec-$stamp@voxera.dev"; password = "SecB!2026xyz"; organization_name = "SecB $stamp"
} | ConvertTo-Json)
$tokenB = $regB.access_token
$hB0 = @{ Authorization = "Bearer $tokenB" }
$meB = Invoke-RestMethod -Uri "$base/auth/me" -Headers $hB0
$tB = (Invoke-RestMethod -Uri "$base/tenants" -Headers $hB0)[0]
if (-not $tB) {
  $tB = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $tokenB"; "Content-Type" = "application/json" } -Body (@{
    organization_id = $meB.organization_id; name = "SecB"; slug = "secb-$stamp"
  } | ConvertTo-Json)
}
$hBT = @{ Authorization = "Bearer $tokenB"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tB.id }

# --- A: No auth -> 401 on every resource
Write-Host ""
Write-Host "[A] Authentication checks" -ForegroundColor Yellow
foreach ($ep in @("/agents","/calls","/evaluations","/debug/reports","/knowledge/documents","/traces")) {
  $code = 0
  try {
    Invoke-RestMethod -Uri "$base$ep" -Headers @{} | Out-Null
    $code = 200
  } catch { $code = $_.Exception.Response.StatusCode.value__ }
  Check "no auth -> $ep returns 401" ($code -eq 401) "got $code"
}

# --- B: Cross-tenant agent
Write-Host ""
Write-Host "[B] Cross-tenant agent access" -ForegroundColor Yellow
if ($agentA) {
  $code = 0
  try {
    Invoke-RestMethod -Uri "$base/agents/$($agentA.id)" -Headers $hBT | Out-Null
    $code = 200
  } catch { $code = $_.Exception.Response.StatusCode.value__ }
  Check "tenant B -> tenant A agent returns 404" ($code -eq 404) "got $code"
} else { Write-Host "  SKIP: no agent" -ForegroundColor DarkYellow }

# --- C: Cross-tenant call
Write-Host ""
Write-Host "[C] Cross-tenant call access" -ForegroundColor Yellow
if ($callA) {
  $code = 0
  try {
    Invoke-RestMethod -Uri "$base/calls/$($callA.id)" -Headers $hBT | Out-Null
    $code = 200
  } catch { $code = $_.Exception.Response.StatusCode.value__ }
  Check "tenant B -> tenant A call returns 404" ($code -eq 404) "got $code"
} else { Write-Host "  SKIP: no call" -ForegroundColor DarkYellow }

# --- D: Cross-tenant evaluation
Write-Host ""
Write-Host "[D] Cross-tenant evaluation access" -ForegroundColor Yellow
if ($dsA) {
  $code = 0
  try {
    Invoke-RestMethod -Uri "$base/evaluations/$($dsA.id)" -Headers $hBT | Out-Null
    $code = 200
  } catch { $code = $_.Exception.Response.StatusCode.value__ }
  Check "tenant B -> tenant A evaluation returns 404" ($code -eq 404) "got $code"
} else { Write-Host "  SKIP: no evaluation" -ForegroundColor DarkYellow }

# --- E: Cross-tenant debug
Write-Host ""
Write-Host "[E] Cross-tenant debug access" -ForegroundColor Yellow
if ($callA) {
  $code = 0
  try {
    Invoke-RestMethod -Uri "$base/debug/calls/$($callA.id)" -Headers $hBT | Out-Null
    $code = 200
  } catch { $code = $_.Exception.Response.StatusCode.value__ }
  Check "tenant B -> tenant A debug returns 404" ($code -eq 404) "got $code"
} else { Write-Host "  SKIP: no call" -ForegroundColor DarkYellow }

# --- F: Knowledge isolation
Write-Host ""
Write-Host "[F] Cross-tenant knowledge isolation" -ForegroundColor Yellow
Set-Content -Path "kb_search.json" -Value '{"query":"pricing","top_k":5}' -Encoding ascii -NoNewline
$resB = curl.exe -s -X POST "$base/knowledge/search" `
  -H "Authorization: Bearer $tokenB" `
  -H "X-Tenant-ID: $($tB.id)" `
  -H "Content-Type: application/json" `
  -d "@kb_search.json" | ConvertFrom-Json
Check "tenant B knowledge search finds 0 tenant A docs" ($resB.results.Count -eq 0) "got $($resB.results.Count)"

# --- G: Member RBAC
Write-Host ""
Write-Host "[G] RBAC: member cannot create agent" -ForegroundColor Yellow
$memberReg = Invoke-RestMethod -Method Post -Uri "$base/users" -Headers $hAT -Body (@{
  organization_id = $meA.organization_id
  email = "m-$stamp@voxera.dev"
  password = "SecB!2026xyz"
  role = "member"
} | ConvertTo-Json)
$mLogin = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -Headers @{ "Content-Type" = "application/json" } -Body (@{
  email = "m-$stamp@voxera.dev"; password = "SecB!2026xyz"
} | ConvertTo-Json)
$hM = @{ Authorization = "Bearer $($mLogin.access_token)"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tA.id }
$code = 0
try {
  Invoke-RestMethod -Method Post -Uri "$base/agents" -Headers $hM -Body (@{
    tenant_id = $tA.id; name = "ShouldFail-$stamp"
  } | ConvertTo-Json) | Out-Null
  $code = 200
} catch { $code = $_.Exception.Response.StatusCode.value__ }
Check "member create agent returns 403" ($code -eq 403) "got $code"

# --- H: Member cannot activate version
Write-Host ""
Write-Host "[H] RBAC: member cannot activate version" -ForegroundColor Yellow
if ($agentA) {
  $versions = Invoke-RestMethod -Uri "$base/agents/$($agentA.id)/versions" -Headers $hAT
  if ($versions.Count -gt 0) {
    $code = 0
    try {
      Invoke-RestMethod -Method Post -Uri "$base/agents/$($agentA.id)/versions/$($versions[0].id)/activate" -Headers $hM -Body "{}" | Out-Null
      $code = 200
    } catch { $code = $_.Exception.Response.StatusCode.value__ }
    Check "member activate version returns 403" ($code -eq 403) "got $code"
  } else { Write-Host "  SKIP: no versions" -ForegroundColor DarkYellow }
}

# --- I: Invalid JWT
Write-Host ""
Write-Host "[I] Invalid JWT" -ForegroundColor Yellow
$code = 0
try {
  Invoke-RestMethod -Uri "$base/auth/me" -Headers @{ Authorization = "Bearer INVALID.TOKEN" } | Out-Null
  $code = 200
} catch { $code = $_.Exception.Response.StatusCode.value__ }
Check "invalid JWT returns 401" ($code -eq 401) "got $code"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan

