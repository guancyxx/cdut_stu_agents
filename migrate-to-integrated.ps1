# Migration Script for Integrated Deployment
Write-Host "========================================"
Write-Host "  QDUOJ + AI Agent Integration"
Write-Host "========================================"
Write-Host ""

Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker not running" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Docker is running" -ForegroundColor Green
Write-Host ""

Write-Host "[2/6] Stopping old QDUOJ services..." -ForegroundColor Yellow
Push-Location qduoj
docker-compose down 2>&1 | Out-Null
Pop-Location
Write-Host "OK: Old QDUOJ stopped" -ForegroundColor Green
Write-Host ""

Write-Host "[3/6] Stopping old AI Agent..." -ForegroundColor Yellow
docker stop cdut-youtu-agent 2>&1 | Out-Null
docker rm cdut-youtu-agent 2>&1 | Out-Null
Write-Host "OK: Old AI Agent stopped" -ForegroundColor Green
Write-Host ""

Write-Host "[4/6] Creating data directories..." -ForegroundColor Yellow
$dirs = @(
    ".\data\submissions",
    ".\data\training", 
    ".\data\chat_history",
    ".\data\problems",
    ".\qduoj\data\backend",
    ".\qduoj\data\postgres",
    ".\qduoj\data\redis",
    ".\qduoj\data\judge_server\log",
    ".\qduoj\data\judge_server\run"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "OK: Directories ready" -ForegroundColor Green
Write-Host ""

Write-Host "[5/6] Pulling Docker images..." -ForegroundColor Yellow
docker-compose pull
Write-Host ""

Write-Host "[6/6] Starting integrated services..." -ForegroundColor Yellow
docker-compose up -d
Write-Host ""

Write-Host "Waiting 30 seconds for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host ""

Write-Host "========================================"
Write-Host "  Service Status"
Write-Host "========================================"
docker-compose ps
Write-Host ""

Write-Host "========================================"
Write-Host "  Access URLs"
Write-Host "========================================"
Write-Host ""
Write-Host "AI Tutoring:  http://localhost:8848" -ForegroundColor Cyan
Write-Host "OJ Platform:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "OJ Admin:     http://localhost:8000/admin" -ForegroundColor Cyan
Write-Host ""
Write-Host "Default Admin: root / rootroot" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================"
Write-Host "  Integration Complete!"
Write-Host "========================================"
Write-Host ""
