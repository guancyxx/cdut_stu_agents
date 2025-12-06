# Scripts 脚本工具索引

## 📂 目录结构

```
scripts/
├── README.md                    # 本索引文档
├── fix_fps_problems.py          # 🔧 修复FPS题目（添加标签）
├── import-fps-native.ps1        # 📥 使用QDUOJ原生FPS导入（推荐）
│
├── test_cases/                  # 📊 测试用例管理
│   ├── add_test_cases.py        # 手动添加单题测试数据
│   ├── batch_add_test_cases.py  # 批量添加测试数据（22题）
│   ├── verify_new_test_cases.py # 验证测试数据正确性
│   └── test_judge.py            # 测试判题流程
│
├── import/                      # 📥 题库导入工具
│   ├── fps_importer.py          # FPS导入核心模块
│   ├── import_fps_v15.py        # 支持FPS v1.5格式导入
│   └── download-fps.ps1         # 下载FPS题库
│
└── archive/                     # 🗂️ 已弃用脚本
    ├── import-fps.ps1           # 旧版导入脚本
    ├── batch-import-fps.ps1     # 旧版批量导入
    ├── import-fps-to-qduoj.ps1  # 旧版导入脚本
    ├── import_fps.py            # 旧版Python导入
    └── import_fps_to_qduoj.py   # 旧版Python导入
```

---

## 🚀 常用脚本

### 1. 导入FPS题库（推荐）

**脚本**: `import-fps-native.ps1`

```powershell
# 基本用法
.\import-fps-native.ps1

# 自定义题库路径
.\import-fps-native.ps1 -FpsDir "d:\custom-fps-path"
```

**功能**:
- ✅ 使用QDUOJ原生FPS解析器
- ✅ 支持FPS v1.1, v1.2, v1.5格式
- ✅ 自动处理测试数据
- ✅ 自动添加标签

**适用场景**: 首次导入题库或批量导入新题目

---

### 2. 修复题目标签

**脚本**: `fix_fps_problems.py`

```bash
docker cp scripts/fix_fps_problems.py cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python /tmp/fix_fps_problems.py
```

**功能**:
- ✅ 智能识别题目类型
- ✅ 自动添加19种标签
- ✅ 调整题目难度
- ✅ 100%题目覆盖

**适用场景**: 题目导入后无标签，需要批量添加标签

---

### 3. 批量添加测试数据

**脚本**: `test_cases/batch_add_test_cases.py`

```bash
docker cp scripts/test_cases/batch_add_test_cases.py cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python /tmp/batch_add_test_cases.py
```

**功能**:
- ✅ 批量为22道题添加测试数据
- ✅ 自动生成.in/.out文件
- ✅ 计算MD5校验
- ✅ 更新数据库

**适用场景**: FPS题目无测试数据文件，需要手动添加

**注意**: 需要修改脚本中的`generate_test_cases()`函数定义测试数据

---

### 4. 单题添加测试数据

**脚本**: `test_cases/add_test_cases.py`

```bash
docker cp scripts/test_cases/add_test_cases.py cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python /tmp/add_test_cases.py
```

**功能**:
- ✅ 为指定题目添加测试数据
- ✅ 灵活自定义测试用例
- ✅ 适合个别题目调整

**适用场景**: 单独为某道题添加或修改测试数据

---

### 5. 验证测试数据

**脚本**: `test_cases/verify_new_test_cases.py`

```bash
docker cp scripts/test_cases/verify_new_test_cases.py cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python /tmp/verify_new_test_cases.py
```

**功能**:
- ✅ 提交正确/错误代码
- ✅ 验证AC/WA判定
- ✅ 检查判题流程
- ✅ 显示详细结果

**适用场景**: 添加测试数据后验证判题是否正常

---

### 6. 测试判题流程

**脚本**: `test_cases/test_judge.py`

```bash
docker cp scripts/test_cases/test_judge.py cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python /tmp/test_judge.py
```

**功能**:
- ✅ 提交测试代码
- ✅ 等待判题完成
- ✅ 显示每个测试用例结果
- ✅ 统计时间/内存

**适用场景**: 调试判题问题或验证系统功能

---

## 📝 脚本使用场景

### 场景1: 首次部署系统

```powershell
# 1. 导入FPS题库
.\import-fps-native.ps1

# 2. 修复题目标签
docker exec cdut-oj-backend python /tmp/fix_fps_problems.py

# 3. 批量添加测试数据（可选）
docker exec cdut-oj-backend python /tmp/batch_add_test_cases.py

# 4. 验证系统功能
docker exec cdut-oj-backend python /tmp/verify_new_test_cases.py
```

---

### 场景2: 添加新题目

```powershell
# 方式1: 导入FPS题库（如果有FPS文件）
.\import-fps-native.ps1 -FpsDir "新题库路径"

# 方式2: 手动在管理后台创建题目
# 然后使用单题添加测试数据脚本
docker exec cdut-oj-backend python /tmp/add_test_cases.py
```

---

### 场景3: 修复题目问题

```powershell
# 问题1: 题目没有标签
docker exec cdut-oj-backend python /tmp/fix_fps_problems.py

# 问题2: 测试数据不足
# 修改 batch_add_test_cases.py 添加更多测试用例
docker exec cdut-oj-backend python /tmp/batch_add_test_cases.py

# 问题3: 判题结果不正确
# 使用验证脚本检查
docker exec cdut-oj-backend python /tmp/verify_new_test_cases.py
```

---

### 场景4: 系统维护

```powershell
# 1. 备份测试数据
docker exec cdut-oj-backend tar -czf /tmp/test_case_backup.tar.gz /data/test_case
docker cp cdut-oj-backend:/tmp/test_case_backup.tar.gz ./backups/

# 2. 检查判题服务
docker logs cdut-oj-judge --tail 50

# 3. 测试判题流程
docker exec cdut-oj-backend python /tmp/test_judge.py
```

---

## 🔧 脚本修改指南

### 添加新的测试数据

编辑 `test_cases/batch_add_test_cases.py`:

```python
def generate_test_cases():
    test_data = {
        # 添加你的题目
        "fps-xxxx": [  # 题目ID
            ("输入1\n", "输出1\n"),
            ("输入2\n", "输出2\n"),
            # ... 更多测试用例
        ],
    }
    return test_data
```

### 修改标签规则

编辑 `fix_fps_problems.py`:

```python
tag_rules = {
    '新标签名': {
        'keywords': ['关键词1', '关键词2'],
        'priority': 5  # 优先级
    }
}
```

---

## ⚠️ 注意事项

### 执行Python脚本前

1. **添加路径**: 所有Python脚本需要 `sys.path.insert(0, '/app')`
2. **Django设置**: 需要正确配置Django环境
3. **数据库访问**: 确保容器内可以访问数据库

### 容器内执行

```bash
# 正确方式：在容器内执行
docker cp scripts/xxx.py cdut-oj-backend:/tmp/
docker exec cdut-oj-backend python /tmp/xxx.py

# 错误方式：直接执行（会找不到Django）
python scripts/xxx.py  # ❌
```

### PowerShell脚本

```powershell
# Windows下执行PowerShell脚本
.\script.ps1

# 如果提示无法执行，设置执行策略
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 📊 脚本执行历史

| 日期 | 脚本 | 结果 | 说明 |
|------|------|------|------|
| 2025-12-02 | import-fps-native.ps1 | ✅ 成功 | 导入609题 |
| 2025-12-02 | fix_fps_problems.py | ✅ 成功 | 添加19种标签 |
| 2025-12-03 | add_test_cases.py | ✅ 成功 | 2题测试数据 |
| 2025-12-03 | batch_add_test_cases.py | ✅ 成功 | 22题测试数据 |
| 2025-12-03 | verify_new_test_cases.py | ✅ 成功 | 验证5题 |
| 2025-12-03 | test_judge.py | ✅ 成功 | 判题测试 |

---

## 🔗 相关文档

- **FPS导入指南**: [../docs/guides/FPS题库导入指南.md](../docs/guides/FPS题库导入指南.md)
- **测试数据报告**: [../docs/reports/批量添加测试数据完成报告.md](../docs/reports/批量添加测试数据完成报告.md)
- **系统状态**: [../docs/CDUT_OJ系统当前状态.md](../docs/CDUT_OJ系统当前状态.md)

---

## 🆘 常见问题

### Q1: 脚本执行失败怎么办？

**A**: 检查以下几点：
1. Docker容器是否运行：`docker ps`
2. 脚本路径是否正确
3. 查看容器日志：`docker logs cdut-oj-backend`

### Q2: 测试数据添加后题目不可见？

**A**: 需要在管理后台设置题目为可见：
- 访问：http://localhost:8000/admin/problem
- 勾选题目 → 操作 → 设为可见

### Q3: 如何批量修改题目？

**A**: 参考 `fix_fps_problems.py` 修改，主要步骤：
1. 查询需要修改的题目
2. 修改题目属性
3. 调用 `problem.save()` 保存

---

**最后更新**: 2025年12月4日  
**维护者**: CDUT Student Agents Team
