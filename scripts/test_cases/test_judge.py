#!/usr/bin/env python3
"""
测试提交代码到OJ系统
模拟用户提交代码并检查判题结果
"""
import sys
sys.path.insert(0, '/app')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oj.settings')

import django
django.setup()

from problem.models import Problem
from submission.models import Submission, JudgeStatus
from account.models import User
from judge.dispatcher import JudgeDispatcher
import time

def submit_code(problem_id, code, language="Python3", username="root"):
    """提交代码到判题系统"""
    
    # 获取题目
    try:
        problem = Problem.objects.get(_id=problem_id)
        print(f"题目: {problem.title}")
        print(f"时间限制: {problem.time_limit}ms")
        print(f"内存限制: {problem.memory_limit}MB")
        print(f"测试用例数: {len(problem.test_case_score)}")
    except Problem.DoesNotExist:
        print(f"错误: 找不到题目 {problem_id}")
        return None
    
    # 获取用户
    try:
        user = User.objects.get(username=username)
        print(f"用户: {user.username}")
    except User.DoesNotExist:
        print(f"错误: 找不到用户 {username}")
        return None
    
    # 创建提交记录
    submission = Submission.objects.create(
        problem=problem,
        user_id=user.id,
        username=user.username,
        code=code,
        language=language,
        result=JudgeStatus.PENDING,
        info={}
    )
    
    print(f"\n提交ID: {submission.id}")
    print(f"状态: {submission.result}")
    print(f"语言: {submission.language}")
    
    # 发送到判题队列
    try:
        JudgeDispatcher(submission.id, problem.id).judge()
        print("✓ 已发送到判题队列")
    except Exception as e:
        print(f"✗ 发送到判题队列失败: {e}")
        return submission
    
    # 等待判题完成（最多30秒）
    print("\n等待判题中", end="", flush=True)
    max_wait = 30
    waited = 0
    
    while waited < max_wait:
        time.sleep(1)
        waited += 1
        print(".", end="", flush=True)
        
        # 刷新提交记录
        submission.refresh_from_db()
        
        # 检查是否判题完成
        if submission.result not in [JudgeStatus.PENDING, JudgeStatus.JUDGING]:
            print(" 完成!")
            break
    else:
        print(" 超时!")
    
    return submission

def print_result(submission):
    """打印判题结果"""
    if not submission:
        return
    
    submission.refresh_from_db()
    
    print("\n" + "=" * 60)
    print("判题结果")
    print("=" * 60)
    print(f"提交ID: {submission.id}")
    print(f"结果: {submission.result}")
    
    result_map = {
        -2: "编译错误 (CE)",
        -1: "错误 (WA)",
        0: "通过 (AC)",
        1: "CPU时间超限 (TLE)",
        2: "真实时间超限 (TLE)",
        3: "内存超限 (MLE)",
        4: "运行错误 (RE)",
        5: "系统错误 (SE)",
        6: "等待中 (PENDING)",
        7: "判题中 (JUDGING)",
        8: "部分通过 (PAC)",
    }
    
    print(f"结果说明: {result_map.get(submission.result, '未知')}")
    
    if submission.statistic_info:
        print(f"\n统计信息:")
        print(f"  时间消耗: {submission.statistic_info.get('time_cost', 'N/A')}ms")
        print(f"  内存消耗: {submission.statistic_info.get('memory_cost', 'N/A')}KB")
        print(f"  通过用例: {submission.statistic_info.get('score', 0)}/{submission.statistic_info.get('test_case_number', 0)}")
    
    if submission.info:
        print(f"\n详细信息:")
        import json
        if isinstance(submission.info, dict) and 'data' in submission.info:
            for idx, case in enumerate(submission.info['data'], 1):
                status = result_map.get(case.get('result', -1), '未知')
                time_cost = case.get('cpu_time', 0)
                memory_cost = case.get('memory', 0)
                print(f"  测试用例 {idx}: {status} (时间: {time_cost}ms, 内存: {memory_cost}KB)")
                
                if case.get('result') != 0:  # 非AC
                    if case.get('error'):
                        print(f"    错误: {case['error'][:100]}")
                    if case.get('output'):
                        print(f"    输出: {case['output'][:100]}")
    
    print("=" * 60)

def main():
    print("=" * 60)
    print("OJ判题流程测试")
    print("=" * 60)
    print()
    
    # 测试1: A+B Problem (正确代码)
    print("【测试1】A+B Problem - 正确代码")
    print("-" * 60)
    
    correct_code = """a, b = map(int, input().split())
print(a + b)"""
    
    print("提交代码:")
    print(correct_code)
    print()
    
    submission1 = submit_code("fps-d16b", correct_code, "Python3")
    print_result(submission1)
    
    print("\n\n")
    
    # 测试2: A+B Problem (错误代码)
    print("【测试2】A+B Problem - 错误代码")
    print("-" * 60)
    
    wrong_code = """a, b = map(int, input().split())
print(a - b)  # 故意写错，减法而非加法"""
    
    print("提交代码:")
    print(wrong_code)
    print()
    
    submission2 = submit_code("fps-d16b", wrong_code, "Python3")
    print_result(submission2)
    
    print("\n\n")
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n访问前台查看提交记录:")
    print(f"http://localhost:8000/submission/{submission1.id if submission1 else 'N/A'}")
    if submission2:
        print(f"http://localhost:8000/submission/{submission2.id}")

if __name__ == '__main__':
    main()
