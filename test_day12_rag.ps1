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
Write-Host "=== Voxera Day 12 - RAG Tests ===" -ForegroundColor Cyan

$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
$tenantId = $tenants[0].id
$h = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json"; "X-Tenant-ID" = $tenantId }

$agents = Invoke-RestMethod -Uri "$base/agents" -Headers $h
$agentId = $agents[0].id

# --- 1) Tool registry has knowledge.search
Write-Host "`n[1] knowledge.search tool registered" -ForegroundColor Yellow
$tools = Invoke-RestMethod -Uri "$base/agents/runtime/tools" -Headers $h
$toolNames = ($tools.tools | ForEach-Object { $_.name }) -join ","
Check "knowledge.search present" ($toolNames -match "knowledge.search")

# --- 2) Upload a document
Write-Host "`n[2] Upload document" -ForegroundColor Yellow
$stamp = [guid]::NewGuid().ToString("N").Substring(0,6)
$docBody = @{
  name = "Voxera FAQ $stamp"
  content = "Voxera is an AI voice agent platform. It supports multi-tenant organizations, versioned agents, and semantic knowledge bases. Pricing starts at $99 per month for Pro. Enterprise pricing is custom."
  source = "faq.md"
  agent_id = $agentId
} | ConvertTo-Json -Depth 5

Set-Content -Path doc_body.json -Value $docBody -Encoding ascii -NoNewline
$doc = curl.exe -s -X POST "$base/knowledge/documents" `
  -H "Authorization: Bearer $token" `
  -H "X-Tenant-ID: $tenantId" `
  -H "Content-Type: application/json" `
  -d "@doc_body.json" | ConvertFrom-Json

Check "doc created" ($doc.id.Length -gt 0)

# --- 3) Chunks created
Write-Host "`n[3] Chunks created" -ForegroundColor Yellow
Start-Sleep -Seconds 2
$chunks = Invoke-RestMethod -Uri "$base/knowledge/documents/$($doc.id)/chunks" -Headers $h
Check "at least one chunk" ($chunks.Count -ge 1)

# --- 4) Embedding dimensions
Write-Host "`n[4] Embedding dimensions" -ForegroundColor Yellow
$dim = docker compose exec postgres psql -U voxera -d voxera -t -c "SELECT vector_dims(embedding) FROM knowledge_chunks WHERE document_id='$($doc.id)' LIMIT 1;"
$dimStr = ($dim -join "").Trim()
Check "embedding is 768-dimensional" ($dimStr -eq "768") "got '$dimStr'"

# --- 5) Semantic search
Write-Host "`n[5] Semantic search" -ForegroundColor Yellow
Start-Sleep -Seconds 2
$searchBody = @{ query = "What is the pricing?"; top_k = 3 } | ConvertTo-Json
Set-Content -Path search_body.json -Value $searchBody -Encoding ascii -NoNewline
$res = curl.exe -s -X POST "$base/knowledge/search" `
  -H "Authorization: Bearer $token" `
  -H "X-Tenant-ID: $tenantId" `
  -H "Content-Type: application/json" `
  -d "@search_body.json" | ConvertFrom-Json

Check "at least one result" ($res.results.Count -ge 1)
Check "result has score" ($res.results[0].score -ge 0)
Write-Host "    top result: score=$($res.results[0].score) doc=$($res.results[0].document_name)"

# --- 6) Cross-tenant isolation
Write-Host "`n[6] Cross-tenant isolation" -ForegroundColor Yellow
$otherStamp = [guid]::NewGuid().ToString("N").Substring(0,8)
$otherReg = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -Headers @{ "Content-Type" = "application/json" } -Body (@{
  email = "rag-$otherStamp@voxera.dev"; password = "password123"; organization_name = "RagOrg $otherStamp"
} | ConvertTo-Json)
$otherToken = $otherReg.access_token
$otherMe = Invoke-RestMethod -Uri "$base/auth/me" -Headers @{ Authorization = "Bearer $otherToken" }
$otherTenants = Invoke-RestMethod -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken" }
if ($otherTenants.Count -eq 0) {
  $ot = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{ Authorization = "Bearer $otherToken"; "Content-Type" = "application/json" } -Body (@{
    organization_id = $otherMe.organization_id; name = "Other"; slug = "rag-$otherStamp"
  } | ConvertTo-Json)
  $otherTenants = @($ot)
}
$otherH = @{ Authorization = "Bearer $otherToken"; "Content-Type" = "application/json"; "X-Tenant-ID" = $otherTenants[0].id }

$searchOther = curl.exe -s -X POST "$base/knowledge/search" `
  -H "Authorization: Bearer $otherToken" `
  -H "X-Tenant-ID: $($otherTenants[0].id)" `
  -H "Content-Type: application/json" `
  -d "@search_body.json" | ConvertFrom-Json
Check "other tenant finds no docs" ($searchOther.results.Count -eq 0) "got $($searchOther.results.Count)"

$crossBlocked = $false
try {
  Invoke-RestMethod -Uri "$base/knowledge/documents/$($doc.id)" -Headers $otherH | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 404) { $crossBlocked = $true }
}
Check "cross-tenant doc -> 404" $crossBlocked

# --- 7) Auth required
Write-Host "`n[7] Auth required" -ForegroundColor Yellow
$noAuth = $false
try {
  Invoke-RestMethod -Uri "$base/knowledge/documents" -Headers @{ "X-Tenant-ID" = $tenantId } | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) { $noAuth = $true }
}
Check "no auth -> 401" $noAuth

# --- 8) Delete document
Write-Host "`n[8] Delete document" -ForegroundColor Yellow
Invoke-RestMethod -Method Delete -Uri "$base/knowledge/documents/$($doc.id)" -Headers $h | Out-Null
$after = Invoke-RestMethod -Uri "$base/knowledge/documents" -Headers $h
$found = $after | Where-Object { $_.id -eq $doc.id }
Check "doc deleted" ($null -eq $found)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan
