#!/usr/bin/env python3
"""
为指定题目添加测试数据的脚本
"""
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oj.settings')

import django
django.setup()

from problem.models import Problem
from django.conf import settings
from utils.shortcuts import rand_str
import hashlib

def create_test_case_for_aplusb():
    """为A+B Problem创建测试数据"""
    
    # 查找题目
    problem = Problem.objects.filter(title__contains='送分题').first()
    if not problem:
        print("错误: 找不到'送分题-A+B Problem'")
        return False
    
    print(f"找到题目: {problem.title} (ID: {problem._id})")
    print(f"原test_case_id: {problem.test_case_id}")
    
    # 创建测试数据目录
    test_case_id = problem.test_case_id
    test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
    
    if not os.path.exists(test_case_dir):
        os.makedirs(test_case_dir, mode=0o710)
        print(f"创建测试数据目录: {test_case_dir}")
    
    # 定义测试数据
    test_cases = [
        {"input": "1 2\n", "output": "3\n"},        # 基本测试
        {"input": "0 0\n", "output": "0\n"},        # 零测试
        {"input": "100 200\n", "output": "300\n"},  # 大数测试
        {"input": "-5 10\n", "output": "5\n"},      # 负数测试
        {"input": "999 1\n", "output": "1000\n"},   # 边界测试
    ]
    
    # 写入测试数据文件
    test_case_info = {"spj": False, "test_cases": {}}
    
    for idx, case in enumerate(test_cases, 1):
        input_content = case["input"]
        output_content = case["output"]
        
        # 写入输入文件
        input_file = os.path.join(test_case_dir, f"{idx}.in")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_content)
        
        # 写入输出文件
        output_file = os.path.join(test_case_dir, f"{idx}.out")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output_content)
        
        # 计算MD5
        stripped_output = output_content.rstrip()
        output_md5 = hashlib.md5(stripped_output.encode("utf-8")).hexdigest()
        
        test_case_info["test_cases"][idx] = {
            "input_name": f"{idx}.in",
            "input_size": len(input_content),
            "output_name": f"{idx}.out",
            "output_size": len(output_content),
            "stripped_output_md5": output_md5
        }
        
        print(f"  创建测试用例 {idx}: {input_content.strip()} → {output_content.strip()}")
    
    # 写入info文件
    import json
    info_file = os.path.join(test_case_dir, "info")
    with open(info_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(test_case_info, indent=4))
    print(f"  写入info文件: {info_file}")
    
    # 更新数据库中的test_case_score
    test_case_score = []
    for idx in range(1, len(test_cases) + 1):
        test_case_score.append({
            "score": 0,  # ACM模式分数为0
            "input_name": f"{idx}.in",
            "output_name": f"{idx}.out"
        })
    
    problem.test_case_score = test_case_score
    problem.visible = True  # 同时设置为可见
    problem.save(update_fields=['test_case_score', 'visible'])
    
    print(f"\n✓ 成功为题目添加 {len(test_cases)} 组测试数据")
    print(f"✓ 题目已设置为可见")
    print(f"✓ 测试数据目录: {test_case_dir}")
    
    # 验证文件
    print("\n验证测试数据文件:")
    for idx in range(1, len(test_cases) + 1):
        in_file = os.path.join(test_case_dir, f"{idx}.in")
        out_file = os.path.join(test_case_dir, f"{idx}.out")
        print(f"  {idx}.in: {os.path.exists(in_file)} (大小: {os.path.getsize(in_file) if os.path.exists(in_file) else 0})")
        print(f"  {idx}.out: {os.path.exists(out_file)} (大小: {os.path.getsize(out_file) if os.path.exists(out_file) else 0})")
    
    return True

def create_test_case_for_narcissistic():
    """为水仙花数创建测试数据"""
    
    # 查找题目
    problem = Problem.objects.filter(title__contains='水仙花数').first()
    if not problem:
        print("警告: 找不到'水仙花数'题目")
        return False
    
    print(f"\n找到题目: {problem.title} (ID: {problem._id})")
    print(f"原test_case_id: {problem.test_case_id}")
    
    # 创建测试数据目录
    test_case_id = problem.test_case_id
    test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
    
    if not os.path.exists(test_case_dir):
        os.makedirs(test_case_dir, mode=0o710)
        print(f"创建测试数据目录: {test_case_dir}")
    
    # 水仙花数：153, 370, 371, 407
    test_cases = [
        {"input": "100 200\n", "output": "153\n"},
        {"input": "300 400\n", "output": "370\n371\n"},
        {"input": "400 410\n", "output": "407\n"},
        {"input": "100 1000\n", "output": "153\n370\n371\n407\n"},
    ]
    
    # 写入测试数据文件
    test_case_info = {"spj": False, "test_cases": {}}
    
    for idx, case in enumerate(test_cases, 1):
        input_content = case["input"]
        output_content = case["output"]
        
        input_file = os.path.join(test_case_dir, f"{idx}.in")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_content)
        
        output_file = os.path.join(test_case_dir, f"{idx}.out")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output_content)
        
        stripped_output = output_content.rstrip()
        output_md5 = hashlib.md5(stripped_output.encode("utf-8")).hexdigest()
        
        test_case_info["test_cases"][idx] = {
            "input_name": f"{idx}.in",
            "input_size": len(input_content),
            "output_name": f"{idx}.out",
            "output_size": len(output_content),
            "stripped_output_md5": output_md5
        }
        
        print(f"  创建测试用例 {idx}: 范围 {input_content.strip()}")
    
    # 写入info文件
    import json
    info_file = os.path.join(test_case_dir, "info")
    with open(info_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(test_case_info, indent=4))
    
    # 更新数据库
    test_case_score = []
    for idx in range(1, len(test_cases) + 1):
        test_case_score.append({
            "score": 0,
            "input_name": f"{idx}.in",
            "output_name": f"{idx}.out"
        })
    
    problem.test_case_score = test_case_score
    problem.visible = True
    problem.save(update_fields=['test_case_score', 'visible'])
    
    print(f"\n✓ 成功为题目添加 {len(test_cases)} 组测试数据")
    print(f"✓ 题目已设置为可见")
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("为测试题目添加测试数据")
    print("=" * 60)
    
    # 添加A+B Problem测试数据
    success1 = create_test_case_for_aplusb()
    
    # 添加水仙花数测试数据
    success2 = create_test_case_for_narcissistic()
    
    if success1 or success2:
        print("\n" + "=" * 60)
        print("测试数据添加完成！")
        print("=" * 60)
        print("\n下一步:")
        print("1. 访问: http://localhost:8000/problem")
        print("2. 查看已启用的题目")
        print("3. 点击题目进入详情页")
        print("4. 提交测试代码验证判题")
        print("\nA+B Problem 测试代码 (Python):")
        print("```python")
        print("a, b = map(int, input().split())")
        print("print(a + b)")
        print("```")
    else:
        print("\n错误: 测试数据添加失败")
