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
Write-Host " Voxera Day 10 - Evaluation Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
$tenantId = $tenants[0].id
$h = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tenantId }

$agents = Invoke-RestMethod -Uri "$base/agents" -Headers $h
$agentId = $agents[0].id
Write-Host "  agent: $agentId ($($agents[0].name))"

$stamp = [guid]::NewGuid().ToString("N").Substring(0,8)

Write-Host ""
Write-Host "[1] Create evaluation dataset" -ForegroundColor Yellow
$ds = Invoke-RestMethod -Method Post -Uri "$base/evaluations" -Headers $h -Body (@{
  name = "Core Tests $stamp"
  description = "Auto-generated for Day 10 tests"
  agent_id = $agentId
} | ConvertTo-Json)
Check "dataset created" ($ds.id.Length -gt 0)

Write-Host ""
Write-Host "[2] Add test cases" -ForegroundColor Yellow
$c1 = Invoke-RestMethod -Method Post -Uri "$base/evaluations/$($ds.id)/cases" -Headers $h -Body (@{
  name = "Current time"
  input_text = "What time is it in UTC?"
  expected_tools = @("get_current_time")
  max_latency_ms = 300000
  enabled = $true
} | ConvertTo-Json)
Check "case 1 created" ($c1.id.Length -gt 0)
Check "case 1 has expected tools" ($c1.expected_tools.Count -ge 1)

$c2 = Invoke-RestMethod -Method Post -Uri "$base/evaluations/$($ds.id)/cases" -Headers $h -Body (@{
  name = "Simple math"
  input_text = "What is 5 plus 5?"
  expected_output = "10"
  expected_tools = @("calculate")
  max_latency_ms = 300000
  enabled = $true
} | ConvertTo-Json)
Check "case 2 created" ($c2.id.Length -gt 0)

Write-Host ""
Write-Host "[3] List test cases" -ForegroundColor Yellow
$list = Invoke-RestMethod -Uri "$base/evaluations/$($ds.id)/cases" -Headers $h
Check "list returns 2 cases" ($list.Count -eq 2)

Write-Host ""
Write-Host "[4] Run evaluation (this can take 5-10 minutes)" -ForegroundColor Yellow
Write-Host "  running..." -ForegroundColor DarkYellow
$t0 = Get-Date
$run = Invoke-RestMethod -Method Post -Uri "$base/evaluations/$($ds.id)/run" -Headers $h -Body "{}"
$elapsed = [int]((Get-Date) - $t0).TotalSeconds
Write-Host "  completed in $elapsed s"

Check "run created" ($run.id.Length -gt 0)
Check "run status completed" ($run.status -eq "completed")
Check "run total_cases = 2" ($run.total_cases -eq 2)
Check "run has pass rate" ($run.pass_rate -ge 0)

Write-Host ""
Write-Host "[5] Results created" -ForegroundColor Yellow
$results = Invoke-RestMethod -Uri "$base/evaluations/$($ds.id)/runs/$($run.id)/results" -Headers $h
Check "results count = 2" ($results.Count -eq 2)
$res1 = $results[0]
Check "result has score" ($res1.score -ge 0)
Check "result has latency_ms" ($res1.latency_ms -gt 0)
Check "result has actual_tools field" ($res1.actual_tools -ne $null)

Write-Host ""
Write-Host "[6] Scoring sanity" -ForegroundColor Yellow
foreach ($r in $results) {
  Write-Host "  case: $($r.input_text.Substring(0, [Math]::Min(40, $r.input_text.Length)))"
  Write-Host "    score=$($r.score) status=$($r.status) latency=$($r.latency_ms)ms"
  Write-Host "    expected_tools=$($r.expected_tools -join ',')  actual_tools=$($r.actual_tools -join ',')"
}
Check "at least one result has score > 0" (($results | Where-Object { $_.score -gt 0 }).Count -ge 1)

Write-Host ""
Write-Host "[7] Tool validation" -ForegroundColor Yellow
$timeResult = $results | Where-Object { $_.expected_tools -contains "get_current_time" }
Check "time case has expected_tools" ($timeResult -ne $null)
if ($timeResult) {
  Check "time case tool_score reflects expectation" ($timeResult.tool_score -ge 0)
}

Write-Host ""
Write-Host "[8] Latency validation" -ForegroundColor Yellow
Check "all results have latency recorded" (($results | Where-Object { $_.latency_ms -gt 0 }).Count -eq 2)

Write-Host ""
Write-Host "[9] Pass/fail calculation" -ForegroundColor Yellow
Check "run pass_rate consistent" (
  [Math]::Abs($run.pass_rate - ($run.passed_cases / [Math]::Max(1, $run.total_cases) * 100)) -lt 0.1
)

Write-Host ""
Write-Host "[10] Evaluation summary" -ForegroundColor Yellow
Check "average_score present" ($run.average_score -ge 0)
Check "avg_latency_ms present" ($run.avg_latency_ms -ge 0)

Write-Host ""
Write-Host "[11] Regression detection" -ForegroundColor Yellow
Write-Host "  running evaluation again to trigger comparison..." -ForegroundColor DarkYellow
$run2 = Invoke-RestMethod -Method Post -Uri "$base/evaluations/$($ds.id)/run" -Headers $h -Body "{}"
Check "second run completed" ($run2.status -eq "completed")
Check "regression fields present" ($run2.regression_details -ne $null)
$hasPrev = $run2.regression_details.previous_run_id -ne $null
Check "regression compared to previous run" $hasPrev
if ($hasPrev) {
  Write-Host "    score: $($run2.regression_details.previous_score) -> $($run2.regression_details.current_score)"
  Write-Host "    pass rate: $($run2.regression_details.previous_pass_rate) -> $($run2.regression_details.current_pass_rate)"
}

Write-Host ""
Write-Host "[12] Tenant isolation" -ForegroundColor Yellow
$otherStamp = [guid]::NewGuid().ToString("N").Substring(0,8)
$otherReg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -Headers @{ "Content-Type" = "application/json" } -Body (@{
  email = "eval-$otherStamp@voxera.dev"
  password = "password123"
  organization_name = "EvalOrg $otherStamp"
} | ConvertTo-Json)
$otherToken = $otherReg.access_token
$otherMe = Invoke-RestMethod -Uri "$base/auth/me" -Headers @{ Authorization = "Bearer $otherToken" }
$otherTenants = Invoke-RestMethod -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken" }
if ($otherTenants.Count -eq 0) {
  $ot = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken"; "Content-Type" = "application/json" } -Body (@{
    organization_id = $otherMe.organization_id
    name = "Other Eval Tenant"
    slug = "eval-$otherStamp"
  } | ConvertTo-Json)
  $otherTenants = @($ot)
}
$crossBlocked = $false
try {
  Invoke-RestMethod -Uri "$base/evaluations/$($ds.id)" -Headers @{
    Authorization = "Bearer $otherToken"
    "X-Tenant-ID" = $otherTenants[0].id
  } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 404) { $crossBlocked = $true }
}
Check "cross-tenant → 404" $crossBlocked

Write-Host ""
Write-Host "[13] Authentication" -ForegroundColor Yellow
$noAuth = $false
try {
  Invoke-RestMethod -Uri "$base/evaluations" -Headers @{ "X-Tenant-ID" = $tenantId } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) { $noAuth = $true }
}
Check "no auth → 401" $noAuth

Write-Host ""
Write-Host "[14] UI assets" -ForegroundColor Yellow
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/js/views/evaluations.js" -UseBasicParsing
Check "evaluations.js served" ($r.StatusCode -eq 200)
Check "has Views.Evaluations" ($r.Content -match "window\.Views\.Evaluations")

$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing
Check "index.html includes evaluations.js" ($r.Content -match "js/views/evaluations\.js")

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""