# 批量导入FPS题库到QDUOJ
# 使用方法: .\batch-import-fps.ps1

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host " FPS题库批量导入到QDUOJ" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
try {
    python --version | Out-Null
} catch {
    Write-Host "❌ Python未安装或不在PATH中" -ForegroundColor Red
    exit 1
}

# 题库文件列表
$fpsFiles = @(
    "fps-problems\fps-zhblue-A+B.xml",
    "fps-problems\fps-examples\fps-my-1000-1128.xml",
    "fps-problems\fps-examples\fps-bas-3001-3482.xml"
)

$outputDir = "qduoj_problems"

Write-Host "📚 将要处理以下题库文件:" -ForegroundColor Yellow
foreach ($file in $fpsFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (不存在)" -ForegroundColor Red
    }
}
Write-Host ""

# 创建输出目录
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

# 处理每个题库文件
$totalProblems = 0
foreach ($file in $fpsFiles) {
    if (Test-Path $file) {
        Write-Host "处理: $file" -ForegroundColor Cyan
        python scripts\import_fps_to_qduoj.py $file $outputDir
        Write-Host ""
    }
}

Write-Host "=====================================" -ForegroundColor Green
Write-Host " ✅ 所有题库处理完成！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 题目已生成到: $outputDir" -ForegroundColor Yellow
Write-Host "📊 统计目录数量..." -ForegroundColor Yellow

$problemCount = (Get-ChildItem -Path $outputDir -Directory | Measure-Object).Count
Write-Host "✓ 共生成 $problemCount 道题目" -ForegroundColor Green
Write-Host ""

Write-Host "下一步操作:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "1. 将题目复制到OJ容器:" -ForegroundColor White
Write-Host "   docker cp $outputDir oj-backend:/app/import_data" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 进入OJ容器:" -ForegroundColor White
Write-Host "   docker exec -it oj-backend bash" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 在容器内执行导入(方式一 - 推荐):" -ForegroundColor White
Write-Host "   访问管理后台 → 题目管理 → 批量导入" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 或使用命令行导入(方式二):" -ForegroundColor White
Write-Host "   cd /app" -ForegroundColor Gray
Write-Host "   python manage.py import_problem /app/import_data" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
