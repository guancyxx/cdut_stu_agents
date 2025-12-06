# FPS 题库导入指南

## 概述

本工具用于将 Free Problem Set (FPS) 格式的题目批量导入到 QDUOJ 在线评测系统。

FPS 题库仓库：https://github.com/zhblue/freeproblemset

## 快速开始

### 第一步：下载 FPS 题库

由于网络原因，建议使用以下几种方式下载：

#### 方式1：使用 Git（推荐）

```bash
git clone https://github.com/zhblue/freeproblemset.git
```

#### 方式2：下载 ZIP 包

访问：https://github.com/zhblue/freeproblemset/archive/refs/heads/master.zip

下载后解压到本地目录，例如：`d:\fps-problems\`

#### 方式3：使用 GitHub 镜像站（国内访问快）

```bash
# 使用 Gitee 镜像（如果有）
git clone https://gitee.com/mirrors/freeproblemset.git

# 或使用其他 GitHub 加速服务
git clone https://ghproxy.com/https://github.com/zhblue/freeproblemset.git
```

### 第二步：确保 OJ 服务运行

```powershell
# 启动 OJ 服务（如果还没启动）
cd d:\cdut_stu_agents
docker-compose up -d

# 检查服务状态
docker-compose ps
```

确保以下服务都在运行：
- ✅ oj-backend
- ✅ oj-judge
- ✅ oj-postgres
- ✅ oj-redis

### 第三步：运行导入脚本

```powershell
# 进入脚本目录
cd d:\cdut_stu_agents\scripts

# 运行导入脚本
.\import-fps.ps1 -FpsDir "d:\fps-problems"

# 自定义OJ地址和管理员账号
.\import-fps.ps1 -FpsDir "d:\fps-problems" -OjUrl "http://localhost:8000" -Username "admin" -Password "yourpassword"
```

## 导入过程

脚本会自动执行以下步骤：

1. **环境检查**
   - 检查 Python 环境（需要 Python 3.7+）
   - 检查必要的依赖包（requests）
   - 检查 OJ 服务状态

2. **扫描题目**
   - 扫描指定目录下的所有 FPS 文件（*.fps 或 *.zip）
   - 显示题目数量和文件列表

3. **批量导入**
   - 逐个解析 FPS 题目文件
   - 转换为 QDUOJ 格式
   - 创建题目并上传测试数据
   - 显示导入进度

4. **统计报告**
   - 显示导入成功/失败数量
   - 列出问题文件（如果有）

## FPS 格式说明

FPS (Free Problem Set) 是一种题目交换格式，每个题目包含：

### 文件结构

```
problem.fps (实际上是一个 ZIP 压缩包)
├── problem.json          # 题目元数据
├── testdata/            # 测试数据目录
│   ├── 1.in            # 测试输入1
│   ├── 1.out           # 测试输出1
│   ├── 2.in            # 测试输入2
│   ├── 2.out           # 测试输出2
│   └── ...
└── attachments/        # 附件（可选）
```

### problem.json 结构

```json
{
  "title": "题目标题",
  "description": "题目描述",
  "input": "输入格式说明",
  "output": "输出格式说明",
  "time_limit": 1000,
  "memory_limit": 256,
  "difficulty": "Low",
  "tags": ["动态规划", "贪心"],
  "source": "题目来源",
  "hint": "提示信息",
  "samples": [
    {
      "input": "样例输入1",
      "output": "样例输出1"
    }
  ]
}
```

## 格式转换映射

| FPS 字段 | QDUOJ 字段 | 说明 |
|---------|-----------|------|
| title | title | 题目标题 |
| description | description | 题目描述 |
| input | input_description | 输入说明 |
| output | output_description | 输出说明 |
| time_limit | time_limit | 时间限制（毫秒） |
| memory_limit | memory_limit | 内存限制（MB） |
| difficulty | difficulty | 难度（Low/Mid/High） |
| tags | tags | 标签数组 |
| source | source | 来源 |
| hint | hint | 提示 |
| samples | samples | 样例数据 |

## 常见问题

### 1. 导入失败：无法连接到 OJ

**原因**：OJ 服务未启动或端口不正确

**解决**：
```powershell
# 检查服务状态
docker-compose ps

# 启动服务
docker-compose up -d

# 检查端口
netstat -ano | findstr "8000"
```

### 2. 导入失败：登录失败

**原因**：管理员账号密码不正确

**解决**：
1. 登录 OJ 管理后台：http://localhost:8000/admin
2. 确认用户名和密码
3. 使用正确的账号运行导入脚本

### 3. 题目导入成功但测试数据上传失败

**原因**：测试数据文件过大或格式问题

**解决**：
1. 检查 FPS 文件中的 testdata 目录是否存在
2. 确认输入输出文件配对（*.in 和 *.out）
3. 检查 QDUOJ 上传限制配置

### 4. 部分题目跳过

**原因**：FPS 文件格式不正确或损坏

**解决**：
1. 检查被跳过的文件是否可以正常解压
2. 确认文件包含 problem.json
3. 手动检查题目数据完整性

## 高级用法

### 1. 只导入特定目录的题目

```powershell
# 只导入特定子目录
.\import-fps.ps1 -FpsDir "d:\fps-problems\dynamic-programming"
```

### 2. 批量导入多个目录

```powershell
# 创建批处理脚本
$directories = @(
    "d:\fps-problems\basic",
    "d:\fps-problems\advanced",
    "d:\fps-problems\competitive"
)

foreach ($dir in $directories) {
    Write-Host "导入：$dir"
    .\import-fps.ps1 -FpsDir $dir
}
```

### 3. 自定义导入配置

修改 `fps_importer.py` 中的以下参数：

```python
# 默认难度映射
difficulty_map = {
    'Low': 'Low',
    'Mid': 'Mid', 
    'High': 'High'
}

# 支持的语言
languages = ['C', 'C++', 'Java', 'Python2', 'Python3']

# 测试用例分数分配策略
# 可以改为其他策略，如指数分配、关键测试点高分等
```

## 预期导入时间

| 题目数量 | 预计时间 |
|---------|---------|
| 10 题 | 1-2 分钟 |
| 50 题 | 5-10 分钟 |
| 100 题 | 10-20 分钟 |
| 500 题 | 1-2 小时 |
| 1000+ 题 | 2-4 小时 |

*时间取决于题目复杂度、测试数据大小和网络速度*

## 导入后的工作

### 1. 验证题目

```powershell
# 访问 OJ 题目列表
# http://localhost:8000/problem

# 检查题目数量、分类、标签
```

### 2. 测试题目

建议对导入的题目进行抽样测试：

1. 随机选择 10-20 道题
2. 提交已知正确的代码
3. 验证判题结果是否正确
4. 检查时间限制和内存限制是否合理

### 3. 完善题目信息

导入后可以通过管理后台完善：

- 调整题目难度分级
- 添加或修改标签
- 补充题解和提示
- 调整时间/内存限制
- 添加题目到题单或比赛

### 4. 分类整理

建议按以下维度整理题目：

1. **知识点分类**
   - 基础语法
   - 数据结构
   - 算法设计
   - 数学问题

2. **难度分级**
   - 入门（100-200题）
   - 基础（200-400题）
   - 提高（200-300题）
   - 竞赛（100-200题）

3. **专题训练**
   - 动态规划专题
   - 图论专题
   - 字符串专题
   - 搜索专题

## 参考资源

- **FPS 官方规范**：https://github.com/zhblue/freeproblemset
- **QDUOJ 文档**：https://docs.onlinejudge.me/
- **题目来源**：
  - Codeforces: https://codeforces.com/
  - AtCoder: https://atcoder.jp/
  - CSES: https://cses.fi/problemset/
  - 洛谷: https://www.luogu.com.cn/

## 故障排查

如果遇到问题，请检查以下日志：

```powershell
# OJ 后端日志
docker-compose logs oj-backend

# 判题服务日志
docker-compose logs oj-judge

# Python 脚本输出
# 运行时会显示在控制台
```

## 联系与支持

如有问题，请查看：
- 项目文档：`docs/`
- 问题追踪：GitHub Issues
- 开发团队：cdut_stu_agents

---

**版本**：1.0.0  
**更新日期**：2025年12月
