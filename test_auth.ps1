$ErrorActionPreference = "Continue"
$base = "http://localhost:8000"
$pass = 0
$fail = 0

function Check($name, $cond, $extra) {
    if ($cond) {
        Write-Host "  PASS: $name" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "  FAIL: $name $extra" -ForegroundColor Red
        $script:fail++
    }
}

function Post($path, $obj, $token) {
    $headers = @{ "Content-Type" = "application/json" }
    if ($token) { $headers["Authorization"] = "Bearer $token" }
    try {
        $r = Invoke-WebRequest -Method Post -Uri "$base$path" -Headers $headers -Body ($obj | ConvertTo-Json -Compress) -UseBasicParsing
        return @{ ok = $true; status = $r.StatusCode; body = ($r.Content | ConvertFrom-Json) }
    } catch {
        return @{ ok = $false; status = $_.Exception.Response.StatusCode.value__ }
    }
}

function Get-Auth($path, $token, $tenantId) {
    $headers = @{ "Authorization" = "Bearer $token" }
    if ($tenantId) { $headers["X-Tenant-ID"] = $tenantId }
    try {
        $r = Invoke-WebRequest -Method Get -Uri "$base$path" -Headers $headers -UseBasicParsing
        return @{ ok = $true; status = $r.StatusCode; body = ($r.Content | ConvertFrom-Json) }
    } catch {
        return @{ ok = $false; status = $_.Exception.Response.StatusCode.value__ }
    }
}

$stamp = [guid]::NewGuid().ToString("N").Substring(0, 8)

Write-Host "`n=== TEST 1: Register ===" -ForegroundColor Cyan
$reg = Post "/auth/register" @{
    email = "owner-$stamp@voxera.dev"
    password = "password123"
    full_name = "Voxera Owner"
    organization_name = "Acme $stamp"
} $null
Check "register returns 201" ($reg.status -eq 201) "got $($reg.status)"
Check "register returns token" ($reg.body.access_token.Length -gt 20) ""
$ownerToken = $reg.body.access_token

Write-Host "`n=== TEST 2: Login ===" -ForegroundColor Cyan
$log = Post "/auth/login" @{ email = "owner-$stamp@voxera.dev"; password = "password123" } $null
Check "login returns 200" ($log.status -eq 200) "got $($log.status)"
Check "login returns token" ($log.body.access_token.Length -gt 20) ""

Write-Host "`n=== TEST 3: Wrong password ===" -ForegroundColor Cyan
$bad = Post "/auth/login" @{ email = "owner-$stamp@voxera.dev"; password = "wrong" } $null
Check "wrong password -> 401" ($bad.status -eq 401) "got $($bad.status)"

Write-Host "`n=== TEST 4: /auth/me ===" -ForegroundColor Cyan
$me = Get-Auth "/auth/me" $ownerToken $null
Check "me returns 200" ($me.status -eq 200) "got $($me.status)"
Check "me role is owner" ($me.body.role -eq "owner") "got $($me.body.role)"

Write-Host "`n=== TEST 5: /agents without JWT ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "$base/agents" -UseBasicParsing
    Check "no token -> 401" $false "got $($r.StatusCode)"
} catch {
    Check "no token -> 401" ($_.Exception.Response.StatusCode.value__ -eq 401) ""
}

Write-Host "`n=== TEST 6: /agents with JWT but no tenant ===" -ForegroundColor Cyan
$noTenant = Get-Auth "/agents" $ownerToken $null
Check "with JWT, missing tenant -> 422" ($noTenant.status -eq 422) "got $($noTenant.status)"

Write-Host "`n=== Setup: tenant + agent ===" -ForegroundColor Cyan
$orgId = $me.body.organization_id
$tenant = Post "/tenants" @{ organization_id = $orgId; name = "Tenant A"; slug = "tenant-a-$stamp" } $ownerToken
Check "tenant created" ($tenant.status -eq 201) "got $($tenant.status)"
$tenantAId = $tenant.body.id

$agent = Post "/agents" @{ tenant_id = $tenantAId; name = "Support Agent" } $ownerToken
Check "agent created by owner" ($agent.status -eq 201) "got $($agent.status)"
$agentAId = $agent.body.id

Write-Host "`n=== TEST 7: Cross-org tenant access ===" -ForegroundColor Cyan
$otherOrg = Post "/auth/register" @{
    email = "other-$stamp@voxera.dev"
    password = "password123"
    organization_name = "Beta $stamp"
} $null
$otherToken = $otherOrg.body.access_token
$cross = Get-Auth "/agents" $otherToken $tenantAId
Check "cross-org tenant -> 404" ($cross.status -eq 404) "got $($cross.status)"

Write-Host "`n=== TEST 8: RBAC ===" -ForegroundColor Cyan
$member = Post "/users" @{
    organization_id = $orgId
    email = "member-$stamp@voxera.dev"
    password = "password123"
    role = "member"
} $ownerToken
Check "member created" ($member.status -eq 201) "got $($member.status)"

$memberLogin = Post "/auth/login" @{ email = "member-$stamp@voxera.dev"; password = "password123" } $null
$memberToken = $memberLogin.body.access_token

try {
    $del = Invoke-WebRequest -Method Delete -Uri "$base/agents/$agentAId" -Headers @{
        "Authorization" = "Bearer $memberToken"
        "X-Tenant-ID" = $tenantAId
    } -UseBasicParsing
    Check "member delete -> 403" $false "got $($del.StatusCode)"
} catch {
    Check "member delete -> 403" ($_.Exception.Response.StatusCode.value__ -eq 403) ""
}

try {
    $del2 = Invoke-WebRequest -Method Delete -Uri "$base/agents/$agentAId" -Headers @{
        "Authorization" = "Bearer $ownerToken"
        "X-Tenant-ID" = $tenantAId
    } -UseBasicParsing
    Check "owner delete -> 204" ($del2.StatusCode -eq 204) "got $($del2.StatusCode)"
} catch {
    Check "owner delete -> 204" $false "got $($_.Exception.Response.StatusCode.value__)"
}

Write-Host ""
Write-Host "=== RESULTS ===" -ForegroundColor Cyan
Write-Host "  Passed: $pass" -ForegroundColor Green
Write-Host "  Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host ""
