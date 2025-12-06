#!/usr/bin/env python3
"""
快速验证新添加的测试数据 - 测试几道题目的判题
"""
import os
import sys
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oj.settings')

import django
django.setup()

from problem.models import Problem
from submission.models import Submission
from judge.dispatcher import JudgeDispatcher
from utils.shortcuts import rand_str
import time

def test_problem(problem_id, code, expected_result):
    """
    测试一道题目
    expected_result: 0=AC, -1=WA
    """
    try:
        problem = Problem.objects.get(_id=problem_id)
        
        # 创建提交
        submission = Submission.objects.create(
            id=rand_str(),
            problem=problem,
            username="test_user",
            user_id=1,
            code=code,
            language="Python3",
            result=-2,  # Pending
            statistic_info={}
        )
        
        # 判题
        JudgeDispatcher(submission.id, problem.id).judge()
        
        # 等待判题完成
        max_wait = 10
        for i in range(max_wait):
            submission.refresh_from_db()
            if submission.result != -2:
                break
            time.sleep(0.5)
        
        # 打印结果
        result_name = {0: "AC", -1: "WA", 1: "TLE", 2: "MLE", 3: "RE", 4: "SE", 5: "CE"}
        actual = result_name.get(submission.result, f"Unknown({submission.result})")
        expected = result_name.get(expected_result, f"Unknown({expected_result})")
        
        success = submission.result == expected_result
        status = "✅" if success else "❌"
        
        print(f"{status} {problem_id}: {problem.title}")
        print(f"   期望: {expected}, 实际: {actual}")
        print(f"   通过: {submission.statistic_info.get('accepted_case_count', 0)}/{len(problem.test_case_score)}")
        print()
        
        return success
        
    except Exception as e:
        print(f"❌ {problem_id}: 测试失败 - {str(e)}")
        print()
        return False

print("=" * 60)
print("快速验证测试数据")
print("=" * 60)
print()

# 测试几道题目
tests = [
    # 1. 你好世界 - 正确代码
    ("fps-4063", 'print("Hello World!")', 0),
    
    # 2. 回文数 - 正确代码
    ("fps-2df6", '''
n = int(input())
s = str(n)
if s == s[::-1]:
    print("yes")
else:
    print("no")
''', 0),
    
    # 3. for循环求和 - 正确代码
    ("fps-124d", '''
n = int(input())
total = sum(range(1, n+1))
print(total)
''', 0),
    
    # 4. 最大公约数 - 正确代码
    ("fps-158c", '''
import math
a, b = map(int, input().split())
print(math.gcd(a, b))
''', 0),
    
    # 5. 字符类型判断 - 错误代码(测试WA)
    ("fps-1386", '''
ch = input()
print("letter")  # 总是输出letter，应该会错
''', -1),
]

success_count = 0
for problem_id, code, expected in tests:
    if test_problem(problem_id, code, expected):
        success_count += 1

print("=" * 60)
print(f"验证完成: {success_count}/{len(tests)} 通过")
print("=" * 60)
