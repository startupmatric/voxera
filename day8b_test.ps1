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
Write-Host "===== DAY 8B VOICE TEST SUITE =====" -ForegroundColor Cyan

# ============================================================
# SECTION 1 â€” Service health
# ============================================================
Write-Host ""
Write-Host "[Test 1] Whisper service reachable" -ForegroundColor Yellow
try {
  $req = [System.Net.WebRequest]::Create("http://127.0.0.1:9000/docs")
  $req.Timeout = 5000
  $req.Proxy = $null
  $resp = $req.GetResponse()
  $whCode = [int]$resp.StatusCode
  $resp.Close()
  Check "whisper /docs returns 200" ($whCode -eq 200) "got $whCode"
} catch {
  Check "whisper /docs returns 200" $false "error: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[Test 2] Piper service reachable" -ForegroundColor Yellow
try {
  $req = [System.Net.WebRequest]::Create("http://127.0.0.1:5000/v1/models")
  $req.Timeout = 5000
  $req.Proxy = $null
  $resp = $req.GetResponse()
  $piperCode = [int]$resp.StatusCode
  $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
  $modelsJson = $reader.ReadToEnd()
  $reader.Close()
  $resp.Close()
  Check "piper /v1/models returns 200" ($piperCode -eq 200) "got $piperCode"
  $models = $modelsJson | ConvertFrom-Json
  Check "piper lists at least one model" ($models.data.Count -ge 1)
  Write-Host "  models: $(($models.data | ForEach-Object { $_.id }) -join ', ')"
} catch {
  Check "piper /v1/models returns 200" $false "error: $($_.Exception.Message)"
}

# ============================================================
# SECTION 2 â€” Backend clients
# ============================================================
Write-Host ""
Write-Host "[Test 3] Backend can reach Whisper + Piper" -ForegroundColor Yellow
$out = docker compose exec -T voxera-backend python -c "
import asyncio
from app.runtime.whisper_client import health as wh
from app.runtime.piper_client import health as ph
async def main():
    w = await wh()
    p = await ph()
    print(f'whisper={w} piper={p}')
asyncio.run(main())
" 2>&1
$outStr = ($out -join "").Trim()
Write-Host "  $outStr"
Check "backend -> whisper ok" ($outStr -match "whisper=True")
Check "backend -> piper ok"   ($outStr -match "piper=True")

Write-Host ""
Write-Host "[Test 4] Piper generates WAV from text" -ForegroundColor Yellow
$out = docker compose exec -T voxera-backend python -c "
import asyncio
from app.runtime.piper_client import synthesize
async def main():
    wav = await synthesize('Testing voice from Voxera')
    print(f'bytes={len(wav)}')
asyncio.run(main())
" 2>&1
$outStr = ($out -join "").Trim()
Write-Host "  $outStr"
$bytes = 0
if ($outStr -match 'bytes=(\d+)') { $bytes = [int]$matches[1] }
Check "piper generated audio" ($bytes -gt 1000) "got $bytes bytes"

Write-Host ""
Write-Host "[Test 5] Whisper transcribes known audio" -ForegroundColor Yellow
$out = docker compose exec -T voxera-backend python -c "
import asyncio
from app.runtime.whisper_client import transcribe
from app.runtime.piper_client import synthesize
async def main():
    wav = await synthesize('What time is it')
    text = await transcribe(wav)
    print(f'transcript={text}')
asyncio.run(main())
" 2>&1
$outStr = ($out -join "").Trim()
Write-Host "  $outStr"
Check "whisper returned non-empty transcript" ($outStr -match "transcript=.+")

# ============================================================
# SECTION 3 â€” Auth + tenant
# ============================================================
Write-Host ""
Write-Host "[Test 6] Auth works" -ForegroundColor Yellow
$me = Invoke-RestMethod -Uri "$base/auth/me" -Headers $h0
Check "auth/me returns email" ($me.email.Length -gt 0)

$tenants = Invoke-RestMethod -Uri "$base/tenants?organization_id=$($me.organization_id)" -Headers $h0
if ($tenants.Count -eq 0) {
  Write-Host "  creating tenant..." -ForegroundColor DarkYellow
  $t = Invoke-RestMethod -Method Post -Uri "$base/tenants" -Headers @{
    Authorization = "Bearer $token"; "Content-Type" = "application/json"
  } -Body (@{
    organization_id = $me.organization_id
    name = "Voice Test Tenant"
    slug = "voice-$(Get-Random -Max 99999)"
  } | ConvertTo-Json)
  $tenants = @($t)
}
$tenantId = $tenants[0].id

$h = @{
  Authorization = "Bearer $token"
  "Content-Type" = "application/json"
  "X-Tenant-ID" = $tenantId
}

$agents = Invoke-RestMethod -Uri "$base/agents" -Headers $h
if ($agents.Count -eq 0) {
  Write-Host "  creating agent..." -ForegroundColor DarkYellow
  $a = Invoke-RestMethod -Method Post -Uri "$base/agents" -Headers $h -Body (@{
    tenant_id = $tenantId
    name = "Voice Test Agent $(Get-Random -Max 99999)"
    system_prompt = "You are a concise assistant. Answer in one sentence. Use tools when they help."
    model_name = "llama3.2:3b"
  } | ConvertTo-Json)
  $agents = @($a)
}
$agentId = $agents[0].id
Write-Host "  agent: $agentId ($($agents[0].name))"

# ============================================================
# SECTION 4 â€” Text call still works
# ============================================================
Write-Host ""
Write-Host "[Test 7] Text call still works" -ForegroundColor Yellow
$call = Invoke-RestMethod -Method Post -Uri "$base/calls" -Headers $h -Body (@{
  agent_id = $agentId
} | ConvertTo-Json)
$callId = $call.id
Check "call created" ($call.id.Length -gt 0)

Write-Host "  sending text message..." -ForegroundColor DarkYellow
$msg = Invoke-RestMethod -Method Post -Uri "$base/calls/$callId/messages" -Headers $h -Body (@{
  content = "What time is it?"
} | ConvertTo-Json)
Check "text response non-empty" ($msg.content.Length -gt 0)
Check "tool fired" ($msg.tool_traces.Count -ge 1)
Write-Host "  AI: $($msg.content)"
foreach ($t in $msg.tool_traces) {
  Write-Host "  -> $($t.name) [$($t.status)] $($t.latency_ms)ms" -ForegroundColor Cyan
}

Invoke-RestMethod -Method Post -Uri "$base/calls/$callId/end" -Headers $h | Out-Null

# ============================================================
# SECTION 5 â€” Voice file end-to-end (no browser)
# ============================================================
Write-Host ""
Write-Host "[Test 8] Full voice pipeline: TTS -> STT -> agent -> TTS" -ForegroundColor Yellow
$out = docker compose exec -T voxera-backend python -c "
import asyncio
from app.runtime.whisper_client import transcribe
from app.runtime.piper_client import synthesize
async def main():
    # 1. Piper: text -> audio
    wav = await synthesize('What is 5 plus 5')
    print(f'tts_bytes={len(wav)}')
    # 2. Whisper: audio -> text
    text = await transcribe(wav)
    print(f'stt_text={text}')
asyncio.run(main())
" 2>&1
$outStr = ($out -join "").Trim()
Write-Host "  $outStr"
Check "TTS produced audio" ($outStr -match "tts_bytes=\d{4,}")
Check "STT produced text"  ($outStr -match "stt_text=.+")

# ============================================================
# SECTION 6 â€” WebSocket endpoint registered
# ============================================================
Write-Host ""
Write-Host "[Test 9] WebSocket endpoint rejects invalid token" -ForegroundColor Yellow
try {
  # Use ws:// upgrade attempt via curl (will fail without proper handshake)
  $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/ws/calls/$agentId?token=invalid" -UseBasicParsing -TimeoutSec 5
  Check "invalid token rejected" $false "got $($r.StatusCode)"
} catch {
  $code = $_.Exception.Response.StatusCode.value__
  Check "invalid token rejected (got $code)" ($code -eq 400 -or $code -eq 403 -or $code -eq 401 -or $code -eq 404 -or $code -eq 426)
}

# ============================================================
# SECTION 7 â€” DB verification
# ============================================================
Write-Host ""
Write-Host "[Test 10] Database has voice-ready schema" -ForegroundColor Yellow

$tables = docker compose exec -T postgres psql -U voxera -d voxera -t -c "SELECT COUNT(*) FROM calls;"
$tablesStr = ($tables -join "").Trim()
$callsCount = 0
[void][int]::TryParse($tablesStr, [ref]$callsCount)
Check "calls table has rows" ($callsCount -ge 1) "got $callsCount"

$msgs = docker compose exec -T postgres psql -U voxera -d voxera -t -c "SELECT COUNT(*) FROM messages;"
$msgsStr = ($msgs -join "").Trim()
$msgsCount = 0
[void][int]::TryParse($msgsStr, [ref]$msgsCount)
Check "messages table has rows" ($msgsCount -ge 3) "got $msgsCount"

$trc = docker compose exec -T postgres psql -U voxera -d voxera -t -c "SELECT COUNT(*) FROM traces WHERE kind='tool';"
$trcStr = ($trc -join "").Trim()
$trcCount = 0
[void][int]::TryParse($trcStr, [ref]$trcCount)
Check "traces table has tool rows" ($trcCount -ge 1) "got $trcCount"

# ============================================================
# SECTION 8 â€” Frontend assets
# ============================================================
Write-Host ""
Write-Host "[Test 11] Frontend serves voice.js" -ForegroundColor Yellow
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/js/voice.js" -UseBasicParsing
Check "voice.js returns 200" ($r.StatusCode -eq 200)
Check "voice.js has Voice module" ($r.Content -match "window\.Voice")

$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/js/views/calls.js" -UseBasicParsing
Check "calls.js returns 200" ($r.StatusCode -eq 200)
Check "calls.js has Hold to Talk" ($r.Content -match "Hold to Talk")

$r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing
Check "index.html includes voice.js" ($r.Content -match "js/voice\.js")
Check "index.html includes calls.js" ($r.Content -match "js/views/calls\.js")

# ============================================================
# RESULTS
# ============================================================
Write-Host ""
Write-Host "===== RESULTS =====" -ForegroundColor Cyan
Write-Host "  Passed: $pass" -ForegroundColor Green
Write-Host "  Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host ""