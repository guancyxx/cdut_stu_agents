#!/usr/bin/env python3
"""
修复FPS导入的题目：
1. 重新生成测试用例数据
2. 添加合适的标签
3. 修复test_case_score
"""
import os
import sys
import re

# Add Django app path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oj.settings')

import django
django.setup()

import xml.etree.ElementTree as ET
from fps.parser import FPSParser as BaseFPSParser, FPSHelper
from problem.models import Problem, ProblemTag
from django.conf import settings
from django.db import transaction
import hashlib

# Extended FPS Parser that supports version 1.5
class ExtendedFPSParser(BaseFPSParser):
    def __init__(self, fps_path=None, string_data=None):
        if fps_path:
            self._etree = ET.parse(fps_path).getroot()
        elif string_data:
            self._etree = ET.fromstring(string_data)
        else:
            raise ValueError("You must provide file path or data")
        
        version = self._etree.attrib.get("version", "No Version")
        if version not in ["1.1", "1.2", "1.5"]:
            raise ValueError(f"Unsupported version '{version}'")

# 标签映射规则
TAG_RULES = {
    # 基础分类
    '入门': ['送分题', 'Hello', '你好', '春节', '春晓', 'A+B'],
    '循环': ['循环', '重复', '次', '遍历', '迭代', 'for', 'while'],
    '条件判断': ['判断', '比较', '如果', 'if', '是否', '选择'],
    '数组': ['数组', '序列', '列表', '矩阵'],
    '字符串': ['字符串', '字符', '单词', '文本', '字母'],
    '数学': ['数学', '计算', '求和', '乘积', '阶乘', '公约数', '公倍数'],
    '排序': ['排序', '从大到小', '从小到大', '升序', '降序'],
    '搜索': ['查找', '搜索', '二分', '寻找'],
    '递归': ['递归', '斐波那契', '汉诺塔'],
    '动态规划': ['背包', '最长', '最短', '路径', 'dp'],
    '贪心': ['贪心', '最优'],
    '图形输出': ['图形', '打印', '输出', '三角形', '矩形', '菱形', '金字塔'],
    '进制转换': ['进制', '二进制', '八进制', '十六进制'],
    '位运算': ['位运算', '异或', '与或非'],
    '模拟': ['模拟', '游戏', '卡牌'],
}

# 难度映射规则
DIFFICULTY_RULES = {
    'Low': ['送分题', '入门', 'Hello', '简单', 'Easy', 'C语言-', '【例'],
    'Mid': ['一般', 'Medium', '练'],
    'High': ['困难', 'Hard', '高级', 'NOIP', 'NOI'],
}

def analyze_tags(title, description):
    """根据题目标题和描述分析应该打的标签"""
    tags = set()
    text = f"{title} {description}".lower()
    
    for tag_name, keywords in TAG_RULES.items():
        for keyword in keywords:
            if keyword.lower() in text:
                tags.add(tag_name)
                break
    
    # 根据题目内容添加额外标签
    if any(word in title for word in ['输入', '输出', 'Input', 'Output']):
        tags.add('输入输出')
    
    if any(word in text for word in ['质数', '素数', '质因数']):
        tags.add('数学')
        tags.add('质数')
    
    if any(word in text for word in ['回文', 'palindrome']):
        tags.add('字符串')
        tags.add('回文')
    
    if any(word in text for word in ['水仙花', '完全数', '幸运数']):
        tags.add('数学')
        tags.add('趣味数字')
    
    # 如果没有任何标签，默认标记为"综合"
    if not tags:
        tags.add('综合')
    
    return list(tags)

def determine_difficulty(title, description):
    """根据题目标题和描述确定难度"""
    from utils.constants import Difficulty
    
    text = f"{title} {description}"
    
    # 检查是否为高难度
    for keyword in DIFFICULTY_RULES['High']:
        if keyword in text:
            return Difficulty.HIGH
    
    # 检查是否为低难度
    for keyword in DIFFICULTY_RULES['Low']:
        if keyword in text:
            return Difficulty.LOW
    
    # 默认中等难度
    return Difficulty.MID

def fix_test_cases(problem, fps_problem_data, helper):
    """修复题目的测试用例"""
    test_case_id = problem.test_case_id
    test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
    
    # 如果目录不存在，创建它
    if not os.path.exists(test_case_dir):
        os.makedirs(test_case_dir, mode=0o710)
        print(f"  创建测试用例目录: {test_case_dir}")
    
    # 保存测试用例
    test_case_info = helper.save_test_case(fps_problem_data, test_case_dir)
    
    # 更新test_case_score
    score = []
    for idx, item in enumerate(test_case_info["test_cases"].values()):
        score.append({
            "score": 0,  # ACM模式下分数为0
            "input_name": item["input_name"],
            "output_name": item.get("output_name")
        })
    
    problem.test_case_score = score
    problem.save(update_fields=['test_case_score'])
    
    return len(score)

def add_tags(problem, tags):
    """为题目添加标签"""
    for tag_name in tags:
        tag_obj, created = ProblemTag.objects.get_or_create(name=tag_name)
        problem.tags.add(tag_obj)
        if created:
            print(f"  创建新标签: {tag_name}")

def process_fps_file(fps_file_path):
    """处理FPS文件，重新导入测试数据和标签"""
    print(f"\n处理文件: {fps_file_path}")
    print("=" * 60)
    
    # 解析FPS文件
    parser = ExtendedFPSParser(fps_file_path)
    problems_data = parser.parse()
    print(f"找到 {len(problems_data)} 个题目")
    
    helper = FPSHelper()
    fixed_count = 0
    
    for idx, problem_data in enumerate(problems_data, 1):
        title = problem_data.get('title', '')
        
        # 查找对应的题目
        try:
            problem = Problem.objects.get(title=title)
        except Problem.DoesNotExist:
            print(f"[{idx}/{len(problems_data)}] 未找到题目: {title}")
            continue
        except Problem.MultipleObjectsReturned:
            # 如果有多个同名题目，取第一个
            problem = Problem.objects.filter(title=title).first()
        
        print(f"\n[{idx}/{len(problems_data)}] 修复: {title}")
        
        # 1. 修复测试用例
        try:
            test_case_count = fix_test_cases(problem, problem_data, helper)
            print(f"  ✓ 测试用例: {test_case_count} 组")
        except Exception as e:
            print(f"  ✗ 测试用例修复失败: {e}")
            continue
        
        # 2. 分析并添加标签
        description = problem_data.get('description', '')
        tags = analyze_tags(title, description)
        add_tags(problem, tags)
        print(f"  ✓ 标签: {', '.join(tags)}")
        
        # 3. 调整难度
        from utils.constants import Difficulty
        old_difficulty = problem.difficulty
        new_difficulty = determine_difficulty(title, description)
        
        if old_difficulty != new_difficulty:
            problem.difficulty = new_difficulty
            problem.save(update_fields=['difficulty'])
            diff_names = {Difficulty.LOW: '简单', Difficulty.MID: '中等', Difficulty.HIGH: '困难'}
            print(f"  ✓ 难度: {diff_names.get(old_difficulty, 'Unknown')} → {diff_names.get(new_difficulty, 'Unknown')}")
        
        fixed_count += 1
    
    return fixed_count

def main():
    print("=" * 60)
    print("FPS题目修复工具")
    print("=" * 60)
    
    # 处理两个FPS文件
    fps_files = [
        '/tmp/fps-my-1000-1128.xml',
        '/tmp/fps-bas-3001-3482.xml'
    ]
    
    total_fixed = 0
    
    for fps_file in fps_files:
        if os.path.exists(fps_file):
            try:
                count = process_fps_file(fps_file)
                total_fixed += count
            except Exception as e:
                print(f"\n处理 {fps_file} 时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n文件不存在: {fps_file}")
    
    print("\n" + "=" * 60)
    print(f"修复完成! 共处理 {total_fixed} 个题目")
    print("=" * 60)
    
    # 统计信息
    print("\n题目统计:")
    print(f"  总题目数: {Problem.objects.count()}")
    print(f"  有测试用例的题目: {Problem.objects.exclude(test_case_score=[]).count()}")
    print(f"  有标签的题目: {Problem.objects.filter(tags__isnull=False).distinct().count()}")
    
    print("\n标签统计:")
    for tag in ProblemTag.objects.all().order_by('-id')[:10]:
        count = tag.problem_set.count()
        print(f"  {tag.name}: {count}题")

if __name__ == '__main__':
    main()
