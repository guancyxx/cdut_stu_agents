# CDUT OJ 系统文档中心

## 📂 文档目录结构

```
docs/
├── README.md                          # 本文档索引
├── CDUT_OJ系统当前状态.md             # 🌟 系统当前状态总览（推荐从这里开始）
├── FPS_IMPORT_GUIDE.md                # FPS题库导入技术指南
├── QDUOJ_DEPLOYED.md                  # QDUOJ部署记录
├── QDUOJ_DEPLOYMENT.md                # QDUOJ部署详细文档
├── QDUOJ_INTEGRATION.md               # QDUOJ集成文档
│
├── reports/                           # 📊 项目报告
│   ├── FPS题库导入完成报告.md         # Phase 2: 609题导入报告
│   ├── FPS题库修复完成报告.md         # Phase 3: 标签系统报告
│   ├── 判题流程测试验证报告.md        # Phase 4: 判题验证报告
│   └── 批量添加测试数据完成报告.md    # Phase 5: 22题测试数据报告
│
├── guides/                            # 📖 使用指南
│   ├── FPS题库导入指南.md             # 如何导入FPS题库
│   ├── 题目推荐使用指南.md            # 教学使用建议（课程大纲）
│   └── 题目管理后台访问指南.md        # 管理员操作手册
│
└── archive/                           # 🗂️ 历史文档
    ├── INTEGRATION_SUCCESS.md         # 旧集成成功文档
    ├── INTEGRATION_SUMMARY.md         # 旧集成摘要
    ├── INTEGRATION_VERIFICATION.md    # 旧集成验证
    ├── INTEGRATED_DEPLOYMENT.md       # 旧集成部署
    ├── QDUOJ_DEPLOYMENT_SUCCESS.md    # 旧部署成功文档
    ├── 中期考核表格.md                # 中期考核材料
    ├── 中期考核表格-更新说明.md       # 中期考核更新
    └── 中期考核表格-术语清理说明.md   # 中期考核术语清理
```

---

## 🚀 快速开始

### 新手入门路径

1. **了解系统状态** → 📄 [CDUT_OJ系统当前状态.md](./CDUT_OJ系统当前状态.md)
   - 系统概况、可用题目、使用建议

2. **开始使用系统** → 📖 [题目推荐使用指南.md](./guides/题目推荐使用指南.md)
   - 按难度分类、课程大纲、学习路径

3. **管理后台操作** → 📖 [题目管理后台访问指南.md](./guides/题目管理后台访问指南.md)
   - 如何管理题目、用户、提交记录

---

## 📊 项目进度报告

### Phase 1: 系统部署 ✅
- 文档: [QDUOJ_DEPLOYMENT.md](./QDUOJ_DEPLOYMENT.md)
- 状态: 完成

### Phase 2: 题库导入 ✅
- 报告: [FPS题库导入完成报告.md](./reports/FPS题库导入完成报告.md)
- 成果: 导入609道题目
- 状态: 完成

### Phase 3: 标签分类 ✅
- 报告: [FPS题库修复完成报告.md](./reports/FPS题库修复完成报告.md)
- 成果: 19个标签分类，100%覆盖
- 状态: 完成

### Phase 4: 判题验证 ✅
- 报告: [判题流程测试验证报告.md](./reports/判题流程测试验证报告.md)
- 成果: AC/WA判定正确
- 状态: 完成

### Phase 5: 测试数据 ✅
- 报告: [批量添加测试数据完成报告.md](./reports/批量添加测试数据完成报告.md)
- 成果: 24题可用（2题手动+22题批量）
- 状态: 完成

### Phase 6: 扩展题库 🔄
- 目标: 扩展到100题
- 状态: 进行中

---

## 📖 按用途分类

### 对于系统管理员

1. **部署与维护**
   - [QDUOJ_DEPLOYMENT.md](./QDUOJ_DEPLOYMENT.md) - 部署指南
   - [CDUT_OJ系统当前状态.md](./CDUT_OJ系统当前状态.md) - 维护指南

2. **题库管理**
   - [FPS_IMPORT_GUIDE.md](./FPS_IMPORT_GUIDE.md) - 导入新题库
   - [题目管理后台访问指南.md](./guides/题目管理后台访问指南.md) - 后台操作

### 对于教师

1. **教学使用**
   - [题目推荐使用指南.md](./guides/题目推荐使用指南.md) - 课程设计
   - [批量添加测试数据完成报告.md](./reports/批量添加测试数据完成报告.md) - 可用题目清单

2. **题目管理**
   - [题目管理后台访问指南.md](./guides/题目管理后台访问指南.md) - 如何编辑题目

### 对于开发者

1. **技术文档**
   - [FPS_IMPORT_GUIDE.md](./FPS_IMPORT_GUIDE.md) - FPS格式说明
   - [QDUOJ_INTEGRATION.md](./QDUOJ_INTEGRATION.md) - 系统集成

2. **测试报告**
   - [判题流程测试验证报告.md](./reports/判题流程测试验证报告.md) - 判题测试
   - 所有reports目录下的文档

---

## 🎯 推荐阅读顺序

### 第一次接触系统

```
1. CDUT_OJ系统当前状态.md          (10分钟) - 了解整体情况
2. 题目推荐使用指南.md             (15分钟) - 看看有什么题目
3. 题目管理后台访问指南.md         (10分钟) - 学会基本操作
```

### 想要深入了解

```
4. 批量添加测试数据完成报告.md     (20分钟) - 了解题目详情
5. 判题流程测试验证报告.md         (15分钟) - 了解判题系统
6. FPS题库导入完成报告.md          (10分钟) - 了解题库来源
```

### 需要扩展题库

```
7. FPS_IMPORT_GUIDE.md             (30分钟) - 学习导入流程
8. FPS题库修复完成报告.md          (10分钟) - 了解标签系统
```

---

## 📞 获取帮助

- **系统问题**: 查看 [CDUT_OJ系统当前状态.md](./CDUT_OJ系统当前状态.md) 的故障排查部分
- **题目问题**: 查看 [题目管理后台访问指南.md](./guides/题目管理后台访问指南.md)
- **导入问题**: 查看 [FPS_IMPORT_GUIDE.md](./FPS_IMPORT_GUIDE.md) 的常见问题部分

---

## 📈 系统状态快照

**最后更新**: 2025年12月3日

- ✅ **系统运行**: 正常
- ✅ **判题服务**: 正常
- ✅ **可用题目**: 24题
- 🟡 **使用阶段**: 小范围试用
- 🎯 **下一目标**: 扩展到50题

---

## 🔗 相关链接

- **OJ访问地址**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin
- **题目列表**: http://localhost:8000/problem
- **提交记录**: http://localhost:8000/status

---

**文档维护**: CDUT Student Agents Team  
**项目仓库**: [QingdaoU/OnlineJudgeDeploy](https://github.com/QingdaoU/OnlineJudgeDeploy)
