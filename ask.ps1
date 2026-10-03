$base = "http://127.0.0.1:8080/api"
$token = (Get-Content token.txt -Raw).Trim()
$h0 = @{ Authorization = "Bearer $token" }
$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
$tenantId = $tenants[0].id
$h = @{
  Authorization = "Bearer $token"
  "Content-Type" = "application/json"
  "X-Tenant-ID" = $tenantId
}
$agentId = "4a030990-8067-4c47-a02c-9f684a6d1cc1"

function Ask($msg) {
  Write-Host ""
  Write-Host ">>> $msg" -ForegroundColor Yellow
  $t0 = Get-Date
  $r = Invoke-RestMethod -Method Post -Uri "$base/agents/$agentId/chat" -Headers $h -Body (@{
    message = $msg
    enable_tools = $true
  } | ConvertTo-Json)
  $dt = [int]((Get-Date) - $t0).TotalMilliseconds
  Write-Host "AI : $($r.response)" -ForegroundColor Green
  Write-Host "     tools: $($r.tool_traces.Count)   latency: $($dt) ms"
  foreach ($t in $r.tool_traces) {
    Write-Host "     -> $($t.name) [$($t.status)] $($t.latency_ms)ms" -ForegroundColor Cyan
    if ($t.error) { Write-Host "        error: $($t.error)" -ForegroundColor Red }
  }
}

Ask "Schedule a meeting called Team Standup for 2026-10-04 at 09:00 UTC."
Ask "What time is it in UTC?"
Ask "What is 234 times 17?"
Ask "Create a new lead for Jane Doe at jane@acme.com from the website."