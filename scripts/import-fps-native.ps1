# QDUOJ FPS Native Import Script
# Use QDUOJ built-in FPS import API

param(
    [string]$FpsFile = "fps-problems\fps-my-1000-1128.xml",
    [string]$AdminUsername = "root",
    [string]$AdminPassword = "rootroot123",
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "QDUOJ FPS Import Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if FPS file exists
if (-not (Test-Path $FpsFile)) {
    Write-Host "Error: FPS file not found: $FpsFile" -ForegroundColor Red
    exit 1
}

$FpsFileName = Split-Path $FpsFile -Leaf
Write-Host "Importing: $FpsFileName" -ForegroundColor Yellow

# Step 1: Get CSRF token and login
Write-Host ""
Write-Host "[Step 1/3] Getting CSRF token and logging in..." -ForegroundColor Green

# First, get CSRF token by accessing the site
try {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $null = Invoke-WebRequest -Uri "$BaseUrl" -SessionVariable session -UseBasicParsing
    
    $csrfToken = $session.Cookies.GetCookies($BaseUrl) | Where-Object { $_.Name -eq "csrftoken" } | Select-Object -ExpandProperty Value
    
    if ($csrfToken) {
        Write-Host "CSRF token obtained: $($csrfToken.Substring(0, [Math]::Min(10, $csrfToken.Length)))..." -ForegroundColor Gray
    }
} catch {
    Write-Host "Warning: Could not get CSRF token: $_" -ForegroundColor Yellow
}

# Login to get JWT token
$loginBody = @{
    username = $AdminUsername
    password = $AdminPassword
} | ConvertTo-Json

try {
    $headers = @{
        "Content-Type" = "application/json"
    }
    
    if ($csrfToken) {
        $headers["X-CSRFToken"] = $csrfToken
    }
    
    $loginResponse = Invoke-RestMethod -Uri "$BaseUrl/api/login" `
        -Method Post `
        -Headers $headers `
        -Body $loginBody `
        -WebSession $session
    
    if ($loginResponse.error) {
        Write-Host "Login failed: $($loginResponse.data)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Login successful!" -ForegroundColor Green
    
    $token = $loginResponse.data.token
    if (-not $token) {
        Write-Host "Warning: No token received" -ForegroundColor Yellow
    } else {
        Write-Host "  Token: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Gray
    }
} catch {
    Write-Host "Login request failed: $_" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Upload FPS file
Write-Host ""
Write-Host "[Step 2/3] Uploading FPS XML file..." -ForegroundColor Green

$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"

# Read file content
$fileContent = [System.IO.File]::ReadAllBytes((Resolve-Path $FpsFile).Path)
$fileName = $FpsFileName

# Build multipart/form-data body
$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: text/xml",
    "",
    [System.Text.Encoding]::UTF8.GetString($fileContent),
    "--$boundary--"
) -join $LF

try {
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    $uploadResponse = Invoke-RestMethod -Uri "$BaseUrl/api/admin/import_fps" `
        -Method Post `
        -Headers $headers `
        -Body $bodyLines `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -WebSession $session
    
    if ($uploadResponse.error) {
        Write-Host "Upload failed: $($uploadResponse.data)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Upload successful!" -ForegroundColor Green
    
    # Display import results
    $importCount = $uploadResponse.data.import_count
    Write-Host ""
    Write-Host "[Step 3/3] Import completed!" -ForegroundColor Green
    Write-Host "Successfully imported problems: $importCount" -ForegroundColor Cyan
    
} catch {
    Write-Host "Upload request failed: $_" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response body: $responseBody" -ForegroundColor Red
    }
    
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Import completed! Visit admin panel to view problems" -ForegroundColor Green
Write-Host "Admin URL: $BaseUrl/admin/problem" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
