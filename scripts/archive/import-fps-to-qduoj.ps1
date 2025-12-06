# QDUOJ FPS题库导入脚本
# 使用QDUOJ原生FPS导入API

param(
    [Parameter(Mandatory=$false)]
    [string]$FpsFile = "fps-problems\fps-my-1000-1128.xml",
    
    [Parameter(Mandatory=$false)]
    [string]$AdminUsername = "root",
    
    [Parameter(Mandatory=$false)]
    [string]$AdminPassword = "rootroot123",
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "QDUOJ FPS题库导入工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查FPS文件是否存在
if (-not (Test-Path $FpsFile)) {
    Write-Host "错误: FPS文件不存在: $FpsFile" -ForegroundColor Red
    exit 1
}

$FpsFileName = Split-Path $FpsFile -Leaf
Write-Host "准备导入: $FpsFileName" -ForegroundColor Yellow

# 步骤1: 登录获取JWT token
Write-Host ""
Write-Host "[步骤1/3] 登录QDUOJ管理员账号..." -ForegroundColor Green

$loginBody = @{
    username = $AdminUsername
    password = $AdminPassword
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$BaseUrl/api/login" `
        -Method Post `
        -Body $loginBody `
        -ContentType "application/json" `
        -SessionVariable session
    
    if ($loginResponse.error) {
        Write-Host "登录失败: $($loginResponse.data)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ 登录成功!" -ForegroundColor Green
    
    # 提取token和csrftoken
    $token = $loginResponse.data.token
    if (-not $token) {
        Write-Host "警告: 未获取到token" -ForegroundColor Yellow
    } else {
        Write-Host "  Token: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Gray
    }
} catch {
    Write-Host "登录请求失败: $_" -ForegroundColor Red
    Write-Host "错误详情: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 步骤2: 上传FPS文件
Write-Host ""
Write-Host "[步骤2/3] 上传FPS XML文件..." -ForegroundColor Green

$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"

# 读取文件内容
$fileContent = [System.IO.File]::ReadAllBytes((Resolve-Path $FpsFile).Path)
$fileName = $FpsFileName

# 构造multipart/form-data请求体
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
        Write-Host "上传失败: $($uploadResponse.data)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ 上传成功!" -ForegroundColor Green
    
    # 显示导入结果
    $importCount = $uploadResponse.data.import_count
    Write-Host ""
    Write-Host "[步骤3/3] 导入完成!" -ForegroundColor Green
    Write-Host "成功导入题目数量: $importCount" -ForegroundColor Cyan
    
} catch {
    Write-Host "上传请求失败: $_" -ForegroundColor Red
    Write-Host "错误详情: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "响应内容: $responseBody" -ForegroundColor Red
    }
    
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "导入完成! 请访问管理后台查看题目" -ForegroundColor Green
Write-Host "管理后台地址: $BaseUrl/admin/problem" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
