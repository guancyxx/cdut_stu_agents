# FPS 题库导入脚本
# 使用方法：.\import-fps.ps1 -FpsDir "题库目录路径"

param(
    [Parameter(Mandatory=$true)]
    [string]$FpsDir,
    
    [string]$OjUrl = "http://localhost:8000",
    [string]$Username = "root",
    [string]$Password = "rootroot"
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "FPS 题库导入工具" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan

# 检查题库目录
if (-not (Test-Path $FpsDir)) {
    Write-Host "❌ 错误：题库目录不存在 $FpsDir" -ForegroundColor Red
    exit 1
}

# 检查Python环境
Write-Host "`n🔍 检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python环境：$pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误：未找到Python，请先安装Python 3.7+" -ForegroundColor Red
    exit 1
}

# 检查必要的Python包
Write-Host "`n🔍 检查依赖包..." -ForegroundColor Yellow
$requiredPackages = @('requests')
$missingPackages = @()

foreach ($package in $requiredPackages) {
    try {
        python -c "import $package" 2>$null
        Write-Host "  ✅ $package" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $package (缺失)" -ForegroundColor Red
        $missingPackages += $package
    }
}

# 安装缺失的包
if ($missingPackages.Count -gt 0) {
    Write-Host "`n📦 安装缺失的包..." -ForegroundColor Yellow
    foreach ($package in $missingPackages) {
        Write-Host "  安装 $package..." -ForegroundColor Yellow
        python -m pip install $package
    }
}

# 检查OJ服务状态
Write-Host "`n🔍 检查OJ服务..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$OjUrl/api/website" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ OJ服务运行正常" -ForegroundColor Green
} catch {
    Write-Host "⚠️  警告：无法连接到OJ服务 ($OjUrl)" -ForegroundColor Yellow
    Write-Host "   请确保OJ服务已启动" -ForegroundColor Yellow
    
    $continue = Read-Host "是否继续？(y/n)"
    if ($continue -ne 'y') {
        exit 1
    }
}

# 统计题目数量
Write-Host "`n📊 统计题目文件..." -ForegroundColor Yellow
$fpsFiles = Get-ChildItem -Path $FpsDir -Recurse -Include "*.fps","*.zip" -File
Write-Host "  发现 $($fpsFiles.Count) 个题目文件" -ForegroundColor Cyan

if ($fpsFiles.Count -eq 0) {
    Write-Host "❌ 错误：未找到题目文件（*.fps 或 *.zip）" -ForegroundColor Red
    exit 1
}

# 显示前5个文件名
Write-Host "`n  前5个文件：" -ForegroundColor Gray
$fpsFiles | Select-Object -First 5 | ForEach-Object {
    Write-Host "    - $($_.Name)" -ForegroundColor Gray
}

# 确认导入
Write-Host ""
$confirm = Read-Host "是否开始导入？(y/n)"
if ($confirm -ne 'y') {
    Write-Host "❌ 取消导入" -ForegroundColor Yellow
    exit 0
}

# 执行导入
Write-Host "`n🚀 开始导入..." -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan

$scriptPath = Join-Path $PSScriptRoot "fps_importer.py"

python $scriptPath $FpsDir --url $OjUrl --username $Username --password $Password

Write-Host "`n✅ 导入完成！" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
