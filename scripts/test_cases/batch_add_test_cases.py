#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量为选中的题目添加测试数据
根据题目类型智能生成测试用例
"""

import os
import sys
import json
import hashlib

# 添加app路径
sys.path.insert(0, '/app')

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
import django
django.setup()

from problem.models import Problem

def md5_file_content(content):
    """计算内容的MD5"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def create_test_case(problem_id, test_cases):
    """
    为指定题目创建测试用例
    test_cases: [(input_str, output_str), ...]
    """
    try:
        problem = Problem.objects.get(_id=problem_id)
        test_case_id = problem.test_case_id
        test_case_dir = f"/data/test_case/{test_case_id}"
        
        # 创建测试数据目录
        os.makedirs(test_case_dir, exist_ok=True)
        
        # 创建测试用例文件
        info_data = {"spj": False, "test_cases": {}}
        
        for i, (input_data, output_data) in enumerate(test_cases, 1):
            # 写入输入文件
            input_file = os.path.join(test_case_dir, f"{i}.in")
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(input_data)
            
            # 写入输出文件
            output_file = os.path.join(test_case_dir, f"{i}.out")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_data)
            
            # 计算MD5
            output_md5 = md5_file_content(output_data)
            
            # 添加到info
            info_data["test_cases"][str(i)] = {
                "input_name": f"{i}.in",
                "input_size": len(input_data.encode('utf-8')),
                "output_name": f"{i}.out",
                "output_size": len(output_data.encode('utf-8')),
                "output_md5": output_md5,
                "stripped_output_md5": md5_file_content(output_data.rstrip())
            }
        
        # 写入info文件
        info_file = os.path.join(test_case_dir, "info")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, indent=4)
        
        # 更新数据库
        problem.test_case_score = [{"score": 100 // len(test_cases), "input_name": f"{i}.in", "output_name": f"{i}.out"} 
                                   for i in range(1, len(test_cases) + 1)]
        problem.visible = True
        problem.save()
        
        print(f"✅ {problem_id}: {problem.title} - 已添加 {len(test_cases)} 个测试用例")
        return True
        
    except Exception as e:
        print(f"❌ {problem_id}: 创建失败 - {str(e)}")
        return False

# ==================== 测试用例定义 ====================

def generate_test_cases():
    """定义所有题目的测试用例"""
    
    test_data = {
        # 1. 入门题目
        "fps-4063": [  # 你好世界
            ("", "Hello World!\n"),
        ],
        
        "fps-2df6": [  # 回文数
            ("121\n", "yes\n"),
            ("123\n", "no\n"),
            ("1221\n", "yes\n"),
            ("12321\n", "yes\n"),
            ("100\n", "no\n"),
        ],
        
        "fps-4180": [  # 卡常数 - 输出所有满足(a+b)^2=原数的四位数
            ("", "3025\n"),  # 只有一个卡常数: 3025 = (30+25)^2
        ],
        
        # 2. 数学题目
        "fps-107d": [  # 计数问题
            ("11 1\n", "4\n"),
            ("20 2\n", "2\n"),
            ("100 0\n", "11\n"),
            ("50 5\n", "5\n"),
        ],
        
        "fps-124d": [  # for循环求和
            ("5\n", "15\n"),  # 1+2+3+4+5=15
            ("10\n", "55\n"),  # 1+...+10=55
            ("1\n", "1\n"),
            ("100\n", "5050\n"),
        ],
        
        "fps-14a5": [  # 明明的随机数
            ("3\n2\n2\n1\n", "2\n1\n2\n"),  # 去重排序
            ("5\n1\n2\n3\n2\n1\n", "3\n1\n2\n3\n"),
            ("1\n5\n", "1\n5\n"),
        ],
        
        "fps-158c": [  # 最大公约数
            ("12 8\n", "4\n"),
            ("15 25\n", "5\n"),
            ("17 19\n", "1\n"),
            ("100 50\n", "50\n"),
        ],
        
        "fps-1767": [  # 损失最小 - 给劫匪m件艺术品，让损失最小(给最便宜的m件)
            ("3 1\n10 20 30\n", "10\n"),  # 3件艺术品，给1件，给最便宜的10
            ("5 2\n100 50 75 25 60\n", "25\n50\n"),  # 给最便宜的2件
            ("12 9\n59 85 76 26 66 92 51 15 2 35 85 49\n", "2\n15\n26\n35\n49\n51\n59\n66\n76\n"),  # 官方样例
        ],
        
        # 3. 循环题目
        "fps-1013": [  # 查找10的位置
            ("4 5 6 7 7 2 3 10 6 10 12 10 10 13\n", "8\n"),
            ("1 2 3 4 5 6 7 8 9 11 12 13 14 15 16 17 18 19 20 21\n", "0\n"),
            ("10 1 2 3\n", "1\n"),
            ("1 2 3 4 5 6 7 8 9 10\n", "10\n"),
        ],
        
        "fps-1cb9": [  # 角谷猜想
            ("5\n", "5 16 8 4 2 1\n"),
            ("1\n", "1\n"),
            ("3\n", "3 10 5 16 8 4 2 1\n"),
        ],
        
        # 4. 条件判断题目
        "fps-1001": [  # 判断正方形
            ("4\n", "16.00\n"),
            ("-3\n", "NO\n"),
            ("0\n", "NO\n"),
            ("5.5\n", "30.25\n"),
        ],
        
        "fps-124c": [  # 收集瓶盖赢大奖 - 10个幸运或20个鼓励可兑奖
            ("11 19\n", "1\n"),  # 11个幸运，可以兑奖
            ("9 19\n", "0\n"),   # 9个幸运，19个鼓励，都不够
            ("5 20\n", "1\n"),   # 20个鼓励，可以兑奖
            ("10 10\n", "1\n"),  # 10个幸运，可以兑奖
            ("0 0\n", "0\n"),    # 都没有
        ],
        
        "fps-1386": [  # 字符类型判断
            ("a\n", "letter\n"),
            ("A\n", "letter\n"),
            ("5\n", "digit\n"),
            ("@\n", "other\n"),
            (" \n", "other\n"),
        ],
        
        # 5. 字符串题目
        "fps-161f": [  # 打印字符
            ("a 3\n", "aaa\n"),
            ("Z 5\n", "ZZZZZ\n"),
            ("* 7\n", "*******\n"),
        ],
        
        "fps-1710": [  # 蜗牛字母
            ("3\n", "a\nbb\nccc\n"),
            ("5\n", "a\nbb\nccc\ndddd\neeeee\n"),
            ("1\n", "a\n"),
        ],
        
        # 6. 数组题目
        "fps-1795": [  # 数组的距离
            ("5\n1 2 3 4 5\n", "4\n"),  # max-min
            ("3\n10 5 8\n", "5\n"),
            ("4\n100 100 100 100\n", "0\n"),
        ],
        
        "fps-1b71": [  # 奇数单增序列
            ("5\n1 2 3 4 5\n", "1 3 5\n"),
            ("6\n2 4 6 8 10 12\n", "\n"),  # 无奇数
            ("4\n1 1 3 5\n", "1 3 5\n"),
        ],
        
        "fps-30a4": [  # 螺旋矩阵 - 输入n行列，输出第i行第j列的值
            ("4 2 3\n", "14\n"),  # 4x4矩阵，第2行第3列是14
            ("3 1 1\n", "1\n"),   # 3x3矩阵，第1行第1列是1
            ("5 3 3\n", "17\n"),  # 5x5矩阵，第3行第3列是17
        ],
        
        # 7. 排序题目
        "fps-32bd": [  # 第n大的数 - 固定数列{99,200,95,87,98,-12,30,87,75,-25}中第n大的数
            ("2\n", "99\n"),   # 官方样例：第2大是99
            ("1\n", "200\n"),  # 第1大是200
            ("3\n", "98\n"),   # 第3大是98
            ("10\n", "-25\n"), # 第10大(最小)是-25
        ],
        
        # 8. 输入输出题目
        "fps-2622": [  # 间隔输出
            ("5\n1 2 3 4 5\n", "1 3 5\n"),
            ("6\n10 20 30 40 50 60\n", "10 30 50\n"),
            ("3\n100 200 300\n", "100 300\n"),
        ],
        
        "fps-2b9c": [  # 输出表达式的值
            ("2 3\n", "5\n"),  # a+b
            ("10 5\n", "15\n"),
            ("0 0\n", "0\n"),
        ],
        
        "fps-2bb8": [  # 倒序输出_1
            ("5\n1 2 3 4 5\n", "5 4 3 2 1\n"),
            ("3\n10 20 30\n", "30 20 10\n"),
            ("1\n100\n", "100\n"),
        ],
    }
    
    return test_data

# ==================== 主程序 ====================

def main():
    print("=" * 60)
    print("批量添加测试数据")
    print("=" * 60)
    print()
    
    test_data = generate_test_cases()
    
    success_count = 0
    fail_count = 0
    
    for problem_id, test_cases in test_data.items():
        if create_test_case(problem_id, test_cases):
            success_count += 1
        else:
            fail_count += 1
        print()
    
    print("=" * 60)
    print(f"完成！成功: {success_count} 题，失败: {fail_count} 题")
    print("=" * 60)

if __name__ == "__main__":
    main()
