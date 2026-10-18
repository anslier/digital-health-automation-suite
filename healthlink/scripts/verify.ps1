param([string]$Email = "john@healthlink.local", [string]$Password = "healthlink-demo-2026")

$ErrorActionPreference = "Stop"

Write-Host "Verifying running HealthLink stack..." -ForegroundColor Cyan

$expectedServices = @("postgres", "backend", "frontend")
$runningServices = @(docker compose ps --status running --services)
if ($LASTEXITCODE -ne 0) { throw "Unable to inspect HealthLink Docker services" }

foreach ($service in $expectedServices) {
    if ($runningServices -notcontains $service) {
        throw "HealthLink service '$service' is not running. Start the stack first with: docker compose up -d --build"
    }
}

Write-Host "PASS Docker services running: $($expectedServices -join ', ')" -ForegroundColor Green

try {
    $frontend = Invoke-WebRequest "http://localhost:4200" -UseBasicParsing -TimeoutSec 10
    if ($frontend.StatusCode -ne 200) {
        throw "Frontend returned HTTP $($frontend.StatusCode)."
    }
    Write-Host "PASS frontend HTTP 200" -ForegroundColor Green
}
catch {
    throw "HealthLink frontend is not reachable at http://localhost:4200. $($_.Exception.Message)"
}

$base = "http://localhost:3000/api"
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = @{ email = $Email; password = $Password; role = "PATIENT" } | ConvertTo-Json
$signedIn = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -WebSession $session -TimeoutSec 10 | Out-Null
        $signedIn = $true
        break
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $signedIn) { throw "Patient sign-in failed. Check credentials and backend logs." }
Write-Host "PASS patient sign-in" -ForegroundColor Green
$doctors = $null
for ($i = 0; $i -lt 15; $i++) {
    try {
        $doctors = Invoke-RestMethod "$base/doctors" -WebSession $session -TimeoutSec 10
        break
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $doctors) {
    throw "HealthLink API did not become ready in time. Run: docker compose logs backend"
}

if ($doctors.Count -lt 1) {
    throw "GET /doctors returned no doctors."
}
Write-Host "PASS GET /doctors ($($doctors.Count) doctors)" -ForegroundColor Green

$before = Invoke-RestMethod "$base/consultations" -WebSession $session -TimeoutSec 10
Write-Host "PASS GET /consultations ($($before.Count) existing consultations)" -ForegroundColor Green

$doctor = $doctors | Where-Object { $_.availability.Count -gt 0 } | Select-Object -First 1
if (-not $doctor) {
    throw "No doctor has a free slot for the booking smoke test."
}
$slot = $doctor.availability | Select-Object -First 1

$body = @{
    doctorId = $doctor.id
    type = "CHAT"
    preferredTime = $slot.startTime
    reasonForVisit = "Automated HealthLink smoke-test consultation."
} | ConvertTo-Json

$created = Invoke-RestMethod "$base/consultations" -Method Post -ContentType "application/json" -Body $body -WebSession $session -TimeoutSec 10
if (-not $created.id) {
    throw "POST /consultations did not return a consultation id."
}
Write-Host "PASS POST /consultations ($($created.id))" -ForegroundColor Green

$after = Invoke-RestMethod "$base/consultations" -WebSession $session -TimeoutSec 10
$persisted = $after | Where-Object { $_.id -eq $created.id }
if (-not $persisted) {
    throw "Created consultation was not returned by GET /consultations."
}
Write-Host "PASS persistence round-trip" -ForegroundColor Green
Write-Host "HealthLink required smoke test passed." -ForegroundColor Green

Invoke-RestMethod "$base/auth/logout" -Method Post -ContentType "application/json" -Body "{}" -WebSession $session | Out-Null
