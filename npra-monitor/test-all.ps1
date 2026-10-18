param(
    [switch]$LiveWorker,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "== NPRA Monitor automated verification ==" -ForegroundColor Cyan

if ($SkipBuild) {
    docker compose up -d
} else {
    docker compose up -d --build
}
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

Write-Host "`n== Compose status ==" -ForegroundColor Cyan
docker compose ps
if ($LASTEXITCODE -ne 0) { throw "docker compose ps failed" }

$workerId = (docker compose ps -q npra-worker).Trim()
if ([string]::IsNullOrWhiteSpace($workerId)) {
    throw "npra-worker container is not present"
}
$workerRunning = (docker inspect -f "{{.State.Running}}" $workerId).Trim()
if ($workerRunning -ne "true") {
    throw "npra-worker is not running"
}
Write-Host "Worker container: RUNNING" -ForegroundColor Green

Write-Host "`n== Unit + integration + browser tests ==" -ForegroundColor Cyan
docker compose -f compose.yaml -f compose.test.yaml run --rm --build npra-tests
if ($LASTEXITCODE -ne 0) { throw "Automated tests failed" }

if ($LiveWorker) {
    Write-Host "`n== Optional live worker queue test ==" -ForegroundColor Yellow
    Write-Host "This creates a real UI-triggered import run. Known successful documents should skip; newly published documents may be processed." -ForegroundColor Yellow

    $baseUrl = "http://localhost:4201"
    $email = if ($env:NPRA_ADMIN_EMAIL) { $env:NPRA_ADMIN_EMAIL } else { "admin@npra.local" }
    $password = if ($env:NPRA_ADMIN_PASSWORD) { $env:NPRA_ADMIN_PASSWORD } else { "npra-demo-2026" }
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

    $loginBody = @{ email = $email; password = $password } | ConvertTo-Json
    Invoke-RestMethod -Uri "$baseUrl/api/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -WebSession $session | Out-Null

    $run = Invoke-RestMethod -Uri "$baseUrl/api/runs" -Method Post -ContentType "application/json" -Body "{}" -WebSession $session
    Write-Host "Queued run $($run.id)" -ForegroundColor Cyan

    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Seconds 2
        $current = Invoke-RestMethod -Uri "$baseUrl/api/runs/$($run.id)" -Method Get -WebSession $session
        Write-Host ("  status={0} discovered={1} skipped={2} processed={3} failed={4}" -f $current.status, $current.discovered_count, $current.skipped_count, $current.processed_count, $current.failed_count)
        if ($current.status -in @("SUCCESS", "PARTIAL", "FAILED")) { break }
    } while ((Get-Date) -lt $deadline)

    if ($current.status -ne "SUCCESS") {
        throw "Live worker run did not finish SUCCESS (final status: $($current.status))"
    }
    Write-Host "Live worker queue: SUCCESS" -ForegroundColor Green
}

Write-Host "`nAll requested NPRA tests passed." -ForegroundColor Green
