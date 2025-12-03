# Integration Test Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Integrated Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: OJ Backend API
Write-Host "[Test 1] OJ Backend API..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/website" -Method Get
    if ($response.data.website_name) {
        Write-Host "OK: OJ API responding - $($response.data.website_name)" -ForegroundColor Green
    }
} catch {
    Write-Host "FAIL: Cannot connect to OJ API" -ForegroundColor Red
}
Write-Host ""

# Test 2: OJ Web Interface
Write-Host "[Test 2] OJ Web Interface..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "OK: OJ web page accessible (Status: $($response.StatusCode))" -ForegroundColor Green
    }
} catch {
    Write-Host "FAIL: Cannot access OJ web page" -ForegroundColor Red
}
Write-Host ""

# Test 3: AI Agent WebUI
Write-Host "[Test 3] AI Agent WebUI..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8848" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "OK: AI Agent WebUI accessible (Status: $($response.StatusCode))" -ForegroundColor Green
    }
} catch {
    Write-Host "FAIL: Cannot access AI Agent WebUI" -ForegroundColor Red
}
Write-Host ""

# Test 4: Container Health
Write-Host "[Test 4] Container Health Status..." -ForegroundColor Yellow
$containers = docker ps --filter "name=cdut-" --format "{{.Names}}:{{.Status}}"
foreach ($container in $containers) {
    $parts = $container -split ':'
    $name = $parts[0]
    $status = $parts[1]
    if ($status -match "healthy|Up") {
        Write-Host "OK: $name - $status" -ForegroundColor Green
    } else {
        Write-Host "WARN: $name - $status" -ForegroundColor Yellow
    }
}
Write-Host ""

# Test 5: Network Connectivity (AI Agent to OJ)
Write-Host "[Test 5] Internal Network Connectivity..." -ForegroundColor Yellow
try {
    $result = docker exec cdut-youtu-agent sh -c "curl -s http://oj-backend:8000/api/website" 2>$null
    if ($result -match "website_name") {
        Write-Host "OK: AI Agent can connect to OJ Backend" -ForegroundColor Green
    } else {
        Write-Host "WARN: Connection may have issues" -ForegroundColor Yellow
    }
} catch {
    Write-Host "FAIL: Cannot test internal connectivity" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  AI Tutoring System: http://localhost:8848" -ForegroundColor Cyan
Write-Host "  OJ Platform:        http://localhost:8000" -ForegroundColor Cyan
Write-Host "  OJ Admin Panel:     http://localhost:8000/admin" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Login to OJ admin: root / rootroot" -ForegroundColor Gray
Write-Host "  2. Change admin password" -ForegroundColor Gray
Write-Host "  3. Create test problems" -ForegroundColor Gray
Write-Host "  4. Test AI Agent integration" -ForegroundColor Gray
Write-Host ""
