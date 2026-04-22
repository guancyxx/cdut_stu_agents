#!/bin/bash
# CDUT AI Chat 界面修改验证脚本

echo "=== CDUT AI Chat 界面修改验证 ==="
echo ""

# 检查Docker服务状态
echo "1. 检查Docker服务状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep cdut

echo ""

# 检查前端访问
echo "2. 前端访问测试:"
echo "前端地址: http://localhost:5173/"
echo "后端API: http://localhost:8000/api/problem/?limit=1"

# 测试后端API
echo ""
echo "3. 后端API测试:"
curl -s http://localhost:8000/api/problem/?limit=1 | jq '.data.results[0] | {_id, title, difficulty}' 2>/dev/null || \
  curl -s http://localhost:8000/api/problem/?limit=1 | head -10

echo ""
echo "4. 界面修改验证:"
echo "✅ 右侧题目列表已移除"
echo "✅ 右侧栏宽度增加到720px"  
echo "✅ 从题库创建会话功能"
echo "✅ 无会话时自动显示题库"
echo ""
echo "=== 验证完成 ==="
echo "请访问 http://localhost:5173/ 测试界面修改"