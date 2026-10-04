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
Write-Host "===== DAY 8 TEST SUITE =====" -ForegroundColor Cyan

# ---------- Pre-flight ----------
Write-Host ""
Write-Host "[Pre-flight] Identity" -ForegroundColor Yellow
$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
Check "auth/me returns email" ($me.email.Length -gt 0) "got '$($me.email)'"
Check "auth/me returns org"   ($me.organization_id.Length -gt 0)
Write-Host "  user: $($me.email)  org: $($me.organization_id)"

# ---------- Test 1: Tenant ----------
Write-Host ""
Write-Host "[Test 1] Tenant exists" -ForegroundColor Yellow
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
if ($tenants.Count -eq 0) {
  Write-Host "  creating tenant..." -ForegroundColor DarkYellow
  $t = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{
    Authorization = "Bearer $token"; "Content-Type" = "application/json"
  } -Body (@{
    organization_id = $me.organization_id
    name = "Bangalore Support"
    slug = "blr-support-$(Get-Random -Max 99999)"
  } | ConvertTo-Json)
  $tenants = @($t)
}
$tenantId = $tenants[0].id
Check "tenant id present" ($tenantId.Length -gt 0)
Write-Host "  tenant: $tenantId"

$h = @{
  Authorization = "Bearer $token"
  "Content-Type" = "application/json"
  "X-Tenant-ID" = $tenantId
}

# ---------- Test 2: Agent ----------
Write-Host ""
Write-Host "[Test 2] Agent exists in tenant" -ForegroundColor Yellow
$agents = Invoke-RestMethod -Uri "$base/agents" -Headers $h
if ($agents.Count -eq 0) {
  Write-Host "  creating agent..." -ForegroundColor DarkYellow
  $a = Invoke-RestMethod -Method Post -Uri "$base/agents" -Headers $h -Body (@{
    tenant_id = $tenantId
    name = "Runtime Demo $(Get-Random -Max 99999)"
    system_prompt = "You are a concise assistant. Answer in one sentence. Use tools when they help."
    model_name = "llama3.2:3b"
  } | ConvertTo-Json)
  $agents = @($a)
}
$agentId = $agents[0].id
Check "agent id present" ($agentId.Length -gt 0)
Write-Host "  agent: $agentId  ($($agents[0].name))"

# ---------- Test 3: Start a call ----------
Write-Host ""
Write-Host "[Test 3] Start a call" -ForegroundColor Yellow
$call = Invoke-RestMethod -Method Post -Uri "$base/calls" -Headers $h -Body (@{
  agent_id = $agentId
} | ConvertTo-Json)
Check "call has id"          ($call.id.Length -gt 0)
Check "status is active"     ($call.status -eq "active")
Check "channel is simulated" ($call.channel -eq "simulated")
$callId = $call.id
Write-Host "  call: $callId"

# ---------- Test 4: Greeting persisted ----------
Write-Host ""
Write-Host "[Test 4] Greeting message persisted" -ForegroundColor Yellow
$detail = Invoke-RestMethod -Uri "$base/calls/$callId" -Headers $h
Check "greeting exists"          ($detail.messages.Count -ge 1)
Check "greeting role=assistant"  ($detail.messages[0].role -eq "assistant")
Check "greeting not empty"       ($detail.messages[0].content.Length -gt 0)
Write-Host "  greeting: $($detail.messages[0].content)"

# ---------- Test 5: Tool fires ----------
Write-Host ""
Write-Host "[Test 5] Send 'What time is it?' -- expect get_current_time tool" -ForegroundColor Yellow
Write-Host "  (this may take 30-90 seconds on CPU)" -ForegroundColor DarkYellow
$t0 = Get-Date
$msg = Invoke-RestMethod -Method Post -Uri "$base/calls/$callId/messages" -Headers $h -Body (@{
  content = "What time is it in UTC?"
} | ConvertTo-Json)
$dt = [int]((Get-Date) - $t0).TotalMilliseconds

Check "assistant response non-empty" ($msg.content.Length -gt 0)
Check "tool_traces count >= 1"       ($msg.tool_traces.Count -ge 1)
$hasTool = $false
foreach ($t in $msg.tool_traces) {
  if ($t.name -eq "get_current_time" -and $t.status -eq "success") { $hasTool = $true }
}
Check "get_current_time ran successfully" $hasTool
Write-Host "  AI: $($msg.content)"
Write-Host "  latency: $dt ms"
foreach ($t in $msg.tool_traces) {
  Write-Host "  -> $($t.name) [$($t.status)] $($t.latency_ms)ms" -ForegroundColor Cyan
}

# ---------- Test 6: Full call history ----------
Write-Host ""
Write-Host "[Test 6] Full call has 3 messages" -ForegroundColor Yellow
$detail = Invoke-RestMethod -Uri "$base/calls/$callId" -Headers $h
Check "message count = 3" ($detail.messages.Count -eq 3) "got $($detail.messages.Count)"
$roles = ($detail.messages | ForEach-Object { $_.role }) -join ","
Check "roles are assistant,user,assistant" ($roles -eq "assistant,user,assistant") "got '$roles'"
foreach ($m in $detail.messages) {
  $n = [Math]::Min(50, $m.content.Length)
  Write-Host "  [$($m.role)] $($m.content.Substring(0, $n))"
}

# ---------- Test 7: Multi-turn ----------
Write-Host ""
Write-Host "[Test 7] Multi-turn -- send 'What is 7 times 8?'" -ForegroundColor Yellow
$msg2 = Invoke-RestMethod -Method Post -Uri "$base/calls/$callId/messages" -Headers $h -Body (@{
  content = "What is 7 times 8?"
} | ConvertTo-Json)
Check "second response non-empty" ($msg2.content.Length -gt 0)
Check "second response has tool"  ($msg2.tool_traces.Count -ge 1)
Write-Host "  AI: $($msg2.content)"

$detail = Invoke-RestMethod -Uri "$base/calls/$callId" -Headers $h
Check "now 5 messages total" ($detail.messages.Count -eq 5) "got $($detail.messages.Count)"

# ---------- Test 8: List calls ----------
Write-Host ""
Write-Host "[Test 8] GET /calls returns the call" -ForegroundColor Yellow
$callList = Invoke-RestMethod -Uri "$base/calls" -Headers $h
$found = $callList | Where-Object { $_.id -eq $callId }
Check "call in list"    ($null -ne $found)
Check "call count >= 1" ($callList.Count -ge 1)

# ---------- Test 9: End call ----------
Write-Host ""
Write-Host "[Test 9] End the call" -ForegroundColor Yellow
$ended = Invoke-RestMethod -Method Post -Uri "$base/calls/$callId/end" -Headers $h
Check "status is ended" ($ended.status -eq "ended")

# ---------- Test 10: Blocked after end ----------
Write-Host ""
Write-Host "[Test 10] Sending to ended call fails" -ForegroundColor Yellow
$blocked = $false
try {
  Invoke-RestMethod -Method Post -Uri "$base/calls/$callId/messages" -Headers $h -Body (@{
    content = "hello"
  } | ConvertTo-Json) | Out-Null
} catch {
  $code = $_.Exception.Response.StatusCode.value__
  if ($code -eq 409) { $blocked = $true }
}
Check "ended call rejects new messages (409)" $blocked

# ---------- Test 11: Missing X-Tenant-ID ----------
Write-Host ""
Write-Host "[Test 11] Missing X-Tenant-ID -> 422" -ForegroundColor Yellow
$noTenant = $false
try {
  Invoke-RestMethod -Uri "$base/calls" -Headers @{ Authorization = "Bearer $token" } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 422) { $noTenant = $true }
}
Check "missing header rejected" $noTenant

# ---------- Test 12: No auth ----------
Write-Host ""
Write-Host "[Test 12] No auth -> 401" -ForegroundColor Yellow
$noAuth = $false
try {
  Invoke-RestMethod -Uri "$base/calls" -Headers @{ "X-Tenant-ID" = $tenantId } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) { $noAuth = $true }
}
Check "no auth rejected" $noAuth

# ---------- Test 13: Cross-tenant ----------
Write-Host ""
Write-Host "[Test 13] Cross-tenant call access -> 404" -ForegroundColor Yellow
$stamp = [guid]::NewGuid().ToString("N").Substring(0,8)
$otherReg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -Headers @{
  "Content-Type" = "application/json"
} -Body (@{
  email = "other-$stamp@voxera.dev"
  password = "password123"
  organization_name = "Other $stamp"
} | ConvertTo-Json)
$otherToken = $otherReg.access_token

$otherMe = Invoke-RestMethod -Uri "$base/auth/me" -Headers @{ Authorization = "Bearer $otherToken" }
$otherTenants = Invoke-RestMethod -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken" }
if ($otherTenants.Count -eq 0) {
  $ot = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{
    Authorization = "Bearer $otherToken"; "Content-Type" = "application/json"
  } -Body (@{
    organization_id = $otherMe.organization_id
    name = "Other Tenant"
    slug = "other-$stamp"
  } | ConvertTo-Json)
  $otherTenants = @($ot)
}
$otherTenantId = $otherTenants[0].id

$crossBlocked = $false
try {
  Invoke-RestMethod -Uri "$base/calls/$callId" -Headers @{
    Authorization = "Bearer $otherToken"
    "X-Tenant-ID" = $otherTenantId
  } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 404) { $crossBlocked = $true }
}
Check "cross-tenant call -> 404" $crossBlocked

# ---------- Test 14: DB verification ----------
Write-Host ""
Write-Host "[Test 14] Database has the call and messages" -ForegroundColor Yellow

$dbCountRaw = docker compose exec -T postgres psql -U voxera -d voxera -t -c "SELECT COUNT(*) FROM messages WHERE call_id='$callId';"
$dbCountStr = ($dbCountRaw -join "").Trim()
Check "5 messages in DB" ($dbCountStr -eq "5") "got '$dbCountStr'"

$traceCountRaw = docker compose exec -T postgres psql -U voxera -d voxera -t -c "SELECT COUNT(*) FROM traces WHERE agent_id='$agentId';"
$traceCountStr = ($traceCountRaw -join "").Trim()
$traceCountInt = 0
[void][int]::TryParse($traceCountStr, [ref]$traceCountInt)
Check "traces recorded for agent" ($traceCountInt -ge 2) "got '$traceCountStr'"

# ---------- Summary ----------
Write-Host ""
Write-Host "===== RESULTS =====" -ForegroundColor Cyan
Write-Host "  Passed: $pass" -ForegroundColor Green
Write-Host "  Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host ""