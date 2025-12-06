# FPS题库导入指南

## 已完成的工作

✅ 成功克隆FPS题库仓库到本地  
✅ 开发Python导入转换脚本  
✅ 成功解析并转换 **609道题目**

### 题库来源

- **fps-my-1000-1128.xml**: 129道题目（入门基础题）
- **fps-bas-3001-3482.xml**: 480道题目（一本通例题和练习）
- 还有更多题库待处理（见下方）

## 快速开始

### 方式一：直接复制到容器并导入（推荐）

```powershell
# 1. 将生成的题目复制到OJ容器
docker cp qduoj_problems oj-backend:/app/import_data

# 2. 进入容器
docker exec -it oj-backend bash

# 3. 在容器内，使用QDUOJ管理后台批量导入
# 访问: http://localhost:8000/admin
# 进入: 题目管理 → 批量导入 → 选择/app/import_data目录
```

### 方式二：使用Web界面导入

1. 登录OJ管理后台：http://localhost:8000/admin
2. 进入「题目管理」
3. 点击「批量导入」按钮
4. 上传题目文件夹或ZIP包

## 已处理题库详情

### 1. fps-my-1000-1128.xml（129题）

**难度级别**: 入门-基础  
**适用对象**: 编程初学者、C语言入门

**知识点覆盖**:
- 基础输入输出
- 条件判断与循环
- 数组与字符串基础
- 简单算法（排序、查找）

**题目示例**:
- 送分题-A+B Problem
- 水仙花数
- 鸡兔同笼
- 求最大公约数
- 图形打印系列

### 2. fps-bas-3001-3482.xml（480题）

**难度级别**: 入门-提高  
**适用对象**: C++竞赛入门、算法学习

**知识点覆盖**:
- 基础语法全覆盖
- 数组与矩阵操作
- 字符串处理
- 递归与回溯
- 动态规划入门
- 贪心算法基础
- 图论入门

**题目来源**: 一本通例题和练习题

## 还可处理的题库

FPS仓库中还有以下题库可以导入：

### 1. fps-www.educg.net-codeforce-1-2833.xml.zip
- **数量**: 约2833题
- **来源**: Codeforces题目
- **难度**: 竞赛级
- **需要**: 先解压ZIP

### 2. fps-zhblue-CSP-J_S 2024系列
- **CSP-J入门级**: 2024年认证题
- **CSP-S提高级**: 2024年认证题
- **需要**: 解压ZIP

### 3. fps-zhblue-SQL.xml
- **数量**: SQL练习题
- **用途**: 数据库学习

### 4. fps-zhblue-一本通 1.1 例题.xml
- **数量**: 一本通系列题目
- **难度**: 基础-提高

## 导入更多题库

### 处理ZIP格式题库

```powershell
# 1. 解压ZIP文件
Expand-Archive -Path "fps-problems\fps-examples\fps-xxx.zip" -DestinationPath "fps-problems\fps-examples\extracted"

# 2. 转换题目
python scripts\import_fps_to_qduoj.py "fps-problems\fps-examples\extracted\题目文件.xml" qduoj_problems

# 3. 复制到容器
docker cp qduoj_problems oj-backend:/app/import_data
```

### 批量处理所有题库

修改 `scripts\batch-import-fps.ps1`，添加更多题库文件：

```powershell
$fpsFiles = @(
    "fps-problems\fps-zhblue-A+B.xml",
    "fps-problems\fps-examples\fps-my-1000-1128.xml",
    "fps-problems\fps-examples\fps-bas-3001-3482.xml",
    # 添加新的题库文件
    "fps-problems\fps-examples\fps-zhblue-SQL.xml",
    "fps-problems\fps-examples\fps-zhblue-一本通 1.1 例题.xml"
)
```

然后运行：
```powershell
.\scripts\batch-import-fps.ps1
```

## 题目结构说明

每道题目包含：

```
problem_XXXX_题目名称/
├── problem.json          # 题目元数据（标题、描述、限制等）
├── testdata/            # 测试数据目录
│   ├── 1.in            # 测试输入1
│   ├── 1.out           # 测试输出1
│   ├── 2.in            # 测试输入2
│   ├── 2.out           # 测试输出2
│   └── ...
└── solution.cpp/.c/.py  # 标程（如果有）
```

## problem.json格式

```json
{
  "title": "题目标题",
  "description": "题目描述",
  "input_description": "输入说明",
  "output_description": "输出说明",
  "samples": [
    {"input": "样例输入", "output": "样例输出"}
  ],
  "hint": "提示信息",
  "time_limit": 1000,      // 时间限制(ms)
  "memory_limit": 256,     // 内存限制(MB)
  "difficulty": "Mid",     // 难度
  "tags": [],              // 标签
  "source": "题目来源",
  "languages": ["C", "C++", "Java", "Python2", "Python3"]
}
```

## 在QDUOJ中导入

### 方法一：管理后台导入（推荐）

1. 登录管理后台
2. 「题目管理」→「批量导入」
3. 选择题目目录或上传ZIP
4. 系统自动识别并导入

### 方法二：命令行导入

```bash
# 在容器内执行
cd /app
python manage.py import_problem /app/import_data/problem_0001_xxx
```

### 方法三：批量导入脚本

```bash
# 批量导入整个目录
cd /app
for dir in /app/import_data/problem_*; do
    python manage.py import_problem "$dir"
done
```

## 导入后的工作

### 1. 题目审核
- 检查题目描述是否正确
- 验证测试数据完整性
- 测试判题功能

### 2. 分类标注
- 添加知识点标签（动态规划、贪心等）
- 标注难度等级
- 归类到题单/专题

### 3. 权限设置
- 设置题目可见性
- 配置比赛使用权限

## 常见问题

### Q1: 导入失败怎么办？
A: 检查题目JSON格式是否正确，测试数据是否完整。

### Q2: 题目太多如何筛选？
A: 建议按知识点和难度分批导入，先导入基础题。

### Q3: 测试数据过大？
A: FPS格式的数据通常已经压缩，如果还是太大，可以减少测试点数量。

### Q4: 如何修改题目？
A: 导入后在管理后台编辑，或修改JSON后重新导入。

## 扩展到3000+题库的路线图

### 第一阶段：基础题库（已完成）
- ✅ 入门题库：129题
- ✅ 基础题库：480题
- **小计**: 609题

### 第二阶段：竞赛题库（1-2周）
- ⏳ Codeforces题库：2833题
- ⏳ CSP认证题：约50题
- **小计**: +2883题 → **总计3492题**

### 第三阶段：专题补充（可选）
- SQL专题
- 一本通其他章节
- 其他开源题库

## 性能建议

### 导入优化
- 分批导入，每批100-200题
- 避免一次性导入3000+题
- 定期备份数据库

### 存储优化
- 定期清理无用测试数据
- 压缩大文件测试数据

## 技术支持

- **FPS格式规范**: https://github.com/zhblue/freeproblemset
- **QDUOJ文档**: https://github.com/QingdaoU/OnlineJudge
- **问题反馈**: 项目GitHub Issues

## 贡献题目

如果你有原创题目，可以：
1. 导出为FPS格式
2. 提交到FPS项目
3. 分享给其他OJ使用

---

**祝你建设题库顺利！🎉**
