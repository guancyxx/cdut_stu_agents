# FPS 题库下载脚本
# 提供多种下载方式

param(
    [string]$OutputDir = "d:\cdut_stu_agents\fps-problems",
    [ValidateSet("git", "zip", "mirror")]
    [string]$Method = "zip"
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "FPS 题库下载工具" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# 创建输出目录
if (-not (Test-Path $OutputDir)) {
    Write-Host "📁 创建目录：$OutputDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "下载方式：$Method" -ForegroundColor Cyan
Write-Host "目标目录：$OutputDir" -ForegroundColor Cyan
Write-Host ""

switch ($Method) {
    "git" {
        Write-Host "📥 使用 Git 克隆..." -ForegroundColor Yellow
        Write-Host "   命令：git clone https://github.com/zhblue/freeproblemset.git" -ForegroundColor Gray
        Write-Host ""
        
        try {
            git clone https://github.com/zhblue/freeproblemset.git $OutputDir
            Write-Host ""
            Write-Host "✅ 下载成功！" -ForegroundColor Green
        } catch {
            Write-Host ""
            Write-Host "❌ Git 克隆失败：$_" -ForegroundColor Red
            Write-Host "   建议：使用 -Method zip 尝试直接下载" -ForegroundColor Yellow
            exit 1
        }
    }
    
    "zip" {
        Write-Host "📥 下载 ZIP 压缩包..." -ForegroundColor Yellow
        $zipUrl = "https://github.com/zhblue/freeproblemset/archive/refs/heads/master.zip"
        $zipFile = Join-Path $env:TEMP "fps-problems.zip"
        
        Write-Host "   URL：$zipUrl" -ForegroundColor Gray
        Write-Host "   临时文件：$zipFile" -ForegroundColor Gray
        Write-Host ""
        
        try {
            Write-Host "   正在下载..." -ForegroundColor Yellow
            
            # 使用多种方式尝试下载
            $downloaded = $false
            
            # 方式1：使用 Invoke-WebRequest
            if (-not $downloaded) {
                try {
                    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -TimeoutSec 300
                    $downloaded = $true
                    Write-Host "   ✅ 下载完成（方式1）" -ForegroundColor Green
                } catch {
                    Write-Host "   ⚠️  方式1失败，尝试其他方式..." -ForegroundColor Yellow
                }
            }
            
            # 方式2：使用 .NET WebClient
            if (-not $downloaded) {
                try {
                    $webClient = New-Object System.Net.WebClient
                    $webClient.DownloadFile($zipUrl, $zipFile)
                    $downloaded = $true
                    Write-Host "   ✅ 下载完成（方式2）" -ForegroundColor Green
                } catch {
                    Write-Host "   ⚠️  方式2失败，尝试其他方式..." -ForegroundColor Yellow
                }
            }
            
            # 方式3：使用代理或镜像
            if (-not $downloaded) {
                $mirrorUrl = "https://ghproxy.com/$zipUrl"
                try {
                    Write-Host "   使用 GitHub 加速镜像..." -ForegroundColor Yellow
                    Invoke-WebRequest -Uri $mirrorUrl -OutFile $zipFile -TimeoutSec 300
                    $downloaded = $true
                    Write-Host "   ✅ 下载完成（镜像）" -ForegroundColor Green
                } catch {
                    Write-Host "   ❌ 所有下载方式均失败" -ForegroundColor Red
                    throw "无法下载题库"
                }
            }
            
            if (-not $downloaded) {
                throw "下载失败"
            }
            
            Write-Host ""
            Write-Host "📦 解压文件..." -ForegroundColor Yellow
            Expand-Archive -Path $zipFile -DestinationPath $OutputDir -Force
            
            # 移动文件到正确位置（解压后的目录名是 freeproblemset-master）
            $extractedDir = Join-Path $OutputDir "freeproblemset-master"
            if (Test-Path $extractedDir) {
                Write-Host "   移动文件到根目录..." -ForegroundColor Yellow
                Get-ChildItem -Path $extractedDir | Move-Item -Destination $OutputDir -Force
                Remove-Item $extractedDir -Recurse -Force
            }
            
            # 清理临时文件
            Remove-Item $zipFile -Force
            
            Write-Host ""
            Write-Host "✅ 下载并解压成功！" -ForegroundColor Green
            
        } catch {
            Write-Host ""
            Write-Host "❌ 下载失败：$_" -ForegroundColor Red
            Write-Host ""
            Write-Host "替代方案：" -ForegroundColor Yellow
            Write-Host "1. 手动下载：https://github.com/zhblue/freeproblemset/archive/refs/heads/master.zip" -ForegroundColor Cyan
            Write-Host "2. 解压到：$OutputDir" -ForegroundColor Cyan
            Write-Host "3. 运行导入脚本：.\import-fps.ps1 -FpsDir `"$OutputDir`"" -ForegroundColor Cyan
            exit 1
        }
    }
    
    "mirror" {
        Write-Host "📥 使用 Gitee 镜像..." -ForegroundColor Yellow
        $mirrorUrl = "https://gitee.com/mirrors/freeproblemset.git"
        
        Write-Host "   URL：$mirrorUrl" -ForegroundColor Gray
        Write-Host ""
        
        try {
            git clone $mirrorUrl $OutputDir
            Write-Host ""
            Write-Host "✅ 下载成功！" -ForegroundColor Green
        } catch {
            Write-Host ""
            Write-Host "❌ 镜像克隆失败：$_" -ForegroundColor Red
            Write-Host "   建议：使用 -Method zip 尝试直接下载" -ForegroundColor Yellow
            exit 1
        }
    }
}

# 统计题目数量
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "📊 题库统计" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan

$fpsFiles = Get-ChildItem -Path $OutputDir -Recurse -Include "*.fps","*.zip" -File
Write-Host "题目文件总数：$($fpsFiles.Count)" -ForegroundColor Cyan

if ($fpsFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "前10个题目文件：" -ForegroundColor Yellow
    $fpsFiles | Select-Object -First 10 | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "✅ 准备就绪！" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：运行导入脚本" -ForegroundColor Yellow
Write-Host "命令：.\import-fps.ps1 -FpsDir `"$OutputDir`"" -ForegroundColor Cyan
Write-Host ""
