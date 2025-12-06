#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPS题库导入QDUOJ脚本

使用方法:
1. 在OJ后端容器中运行: docker exec -it oj-backend bash
2. 将FPS XML文件复制到容器: docker cp fps-file.xml oj-backend:/tmp/
3. 在容器中运行: python import_fps_to_qduoj.py /tmp/fps-file.xml
"""

import xml.etree.ElementTree as ET
import os
import sys
import re
import html
from pathlib import Path


def clean_html(text):
    """清理HTML内容"""
    if not text:
        return ""
    # 移除CDATA标记
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    # 解码HTML实体
    text = html.unescape(text)
    return text.strip()


def parse_fps_xml(xml_file):
    """解析FPS XML文件"""
    print(f"正在解析文件: {xml_file}")
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ XML解析失败: {e}")
        return []
    
    problems = []
    items = root.findall('.//item')
    
    print(f"发现 {len(items)} 道题目")
    
    for idx, item in enumerate(items, 1):
        try:
            problem = {}
            
            # 基本信息
            problem['title'] = clean_html(item.findtext('title', ''))
            problem['source'] = clean_html(item.findtext('source', ''))
            
            # 时间和内存限制
            time_limit = item.find('time_limit')
            if time_limit is not None:
                time_value = clean_html(time_limit.text)
                time_unit = time_limit.get('unit', 's')
                if time_unit == 's':
                    problem['time_limit'] = int(float(time_value) * 1000)  # 转换为ms
                else:
                    problem['time_limit'] = int(float(time_value))
            else:
                problem['time_limit'] = 1000
            
            memory_limit = item.find('memory_limit')
            if memory_limit is not None:
                memory_value = clean_html(memory_limit.text)
                memory_unit = memory_limit.get('unit', 'mb')
                if memory_unit == 'mb':
                    problem['memory_limit'] = int(float(memory_value))
                elif memory_unit == 'kb':
                    problem['memory_limit'] = int(float(memory_value) / 1024)
                else:
                    problem['memory_limit'] = int(float(memory_value))
            else:
                problem['memory_limit'] = 256
            
            # 题目描述
            problem['description'] = clean_html(item.findtext('description', ''))
            problem['input'] = clean_html(item.findtext('input', ''))
            problem['output'] = clean_html(item.findtext('output', ''))
            problem['hint'] = clean_html(item.findtext('hint', ''))
            
            # 样例
            problem['samples'] = []
            sample_inputs = item.findall('sample_input')
            sample_outputs = item.findall('sample_output')
            
            for s_in, s_out in zip(sample_inputs, sample_outputs):
                problem['samples'].append({
                    'input': clean_html(s_in.text),
                    'output': clean_html(s_out.text)
                })
            
            # 测试数据
            problem['test_cases'] = []
            test_inputs = item.findall('test_input')
            test_outputs = item.findall('test_output')
            
            for t_idx, (t_in, t_out) in enumerate(zip(test_inputs, test_outputs), 1):
                test_name = t_in.get('name', f'test_{t_idx:02d}')
                problem['test_cases'].append({
                    'name': test_name,
                    'input': clean_html(t_in.text),
                    'output': clean_html(t_out.text)
                })
            
            # Special Judge (如果有)
            spj = item.find('spj')
            if spj is not None:
                problem['spj'] = clean_html(spj.text)
                problem['spj_language'] = spj.get('language', 'C++')
            
            # 标程 (如果有)
            solution = item.find('solution')
            if solution is not None:
                problem['solution'] = clean_html(solution.text)
                problem['solution_language'] = solution.get('language', 'C++')
            
            problems.append(problem)
            print(f"✓ [{idx}/{len(items)}] {problem['title']}")
            
        except Exception as e:
            print(f"✗ [{idx}/{len(items)}] 解析失败: {e}")
            continue
    
    return problems


def generate_qduoj_import_format(problems, output_dir):
    """生成QDUOJ导入格式的文件"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for idx, problem in enumerate(problems, 1):
        problem_dir = output_path / f"problem_{idx:04d}_{sanitize_filename(problem['title'])}"
        problem_dir.mkdir(exist_ok=True)
        
        # 创建problem.json
        import json
        problem_json = {
            "title": problem['title'],
            "description": problem['description'],
            "input_description": problem['input'],
            "output_description": problem['output'],
            "samples": problem['samples'],
            "hint": problem['hint'],
            "time_limit": problem['time_limit'],
            "memory_limit": problem['memory_limit'],
            "difficulty": "Mid",  # 默认中等难度
            "tags": [],
            "source": problem.get('source', ''),
            "spj": problem.get('spj') is not None,
            "spj_language": problem.get('spj_language', 'C++'),
            "spj_code": problem.get('spj', ''),
            "languages": ["C", "C++", "Java", "Python2", "Python3"]
        }
        
        with open(problem_dir / 'problem.json', 'w', encoding='utf-8') as f:
            json.dump(problem_json, f, ensure_ascii=False, indent=2)
        
        # 创建测试数据目录
        testdata_dir = problem_dir / 'testdata'
        testdata_dir.mkdir(exist_ok=True)
        
        # 写入测试数据
        for test_idx, test_case in enumerate(problem['test_cases'], 1):
            in_file = testdata_dir / f"{test_idx}.in"
            out_file = testdata_dir / f"{test_idx}.out"
            
            with open(in_file, 'w', encoding='utf-8') as f:
                f.write(test_case['input'])
            
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(test_case['output'])
        
        # 如果有标程，保存
        if 'solution' in problem:
            ext_map = {
                'C': '.c',
                'C++': '.cpp',
                'Java': '.java',
                'Python': '.py',
                'Python2': '.py',
                'Python3': '.py'
            }
            lang = problem.get('solution_language', 'C++')
            ext = ext_map.get(lang, '.cpp')
            
            with open(problem_dir / f'solution{ext}', 'w', encoding='utf-8') as f:
                f.write(problem['solution'])
        
        print(f"✓ 生成第 {idx} 题: {problem['title']}")
    
    print(f"\n✅ 成功生成 {len(problems)} 道题目到目录: {output_path}")
    return output_path


def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    # 移除或替换Windows文件名中的非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    # 限制长度
    return filename[:50]


def import_to_qduoj_via_api(problems, api_url, admin_token):
    """通过QDUOJ API导入题目（需要在容器内运行或有网络访问）"""
    import requests
    
    headers = {
        'Authorization': f'Bearer {admin_token}',
        'Content-Type': 'application/json'
    }
    
    success_count = 0
    
    for idx, problem in enumerate(problems, 1):
        try:
            # 构建API请求数据
            data = {
                "title": problem['title'],
                "description": problem['description'],
                "input_description": problem['input'],
                "output_description": problem['output'],
                "samples": problem['samples'],
                "hint": problem['hint'],
                "time_limit": problem['time_limit'],
                "memory_limit": problem['memory_limit'],
                "difficulty": "Mid",
                "visible": True,
                "tags": [],
                "source": problem.get('source', ''),
                "spj": problem.get('spj') is not None,
                "languages": ["C", "C++", "Java", "Python2", "Python3"]
            }
            
            # 调用API创建题目
            response = requests.post(
                f"{api_url}/api/admin/problem",
                json=data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                problem_id = result['data']['id']
                
                # 上传测试数据
                upload_test_data(api_url, admin_token, problem_id, problem['test_cases'])
                
                success_count += 1
                print(f"✓ [{idx}/{len(problems)}] {problem['title']} (ID: {problem_id})")
            else:
                print(f"✗ [{idx}/{len(problems)}] {problem['title']} - API错误: {response.status_code}")
        
        except Exception as e:
            print(f"✗ [{idx}/{len(problems)}] {problem['title']} - 导入失败: {e}")
    
    print(f"\n✅ 成功导入 {success_count}/{len(problems)} 道题目")


def upload_test_data(api_url, admin_token, problem_id, test_cases):
    """上传测试数据到QDUOJ"""
    # 这里需要根据QDUOJ的具体API实现
    # 通常是打包成zip上传
    pass


def main():
    if len(sys.argv) < 2:
        print("用法: python import_fps_to_qduoj.py <fps_xml_file> [output_dir]")
        print("\n示例:")
        print("  python import_fps_to_qduoj.py fps-problems/fps-zhblue-A+B.xml")
        print("  python import_fps_to_qduoj.py fps-problems/fps-examples/fps-my-1000-1128.xml ./output")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './qduoj_import_data'
    
    if not os.path.exists(xml_file):
        print(f"❌ 文件不存在: {xml_file}")
        sys.exit(1)
    
    # 解析FPS XML
    problems = parse_fps_xml(xml_file)
    
    if not problems:
        print("❌ 未能解析到任何题目")
        sys.exit(1)
    
    print(f"\n成功解析 {len(problems)} 道题目")
    
    # 生成QDUOJ导入格式
    print("\n正在生成QDUOJ导入文件...")
    output_path = generate_qduoj_import_format(problems, output_dir)
    
    print("\n" + "="*60)
    print("下一步操作:")
    print("="*60)
    print(f"1. 题目文件已生成到: {output_path}")
    print(f"2. 将整个目录复制到OJ容器:")
    print(f"   docker cp {output_path} oj-backend:/app/import_data")
    print(f"3. 进入OJ容器:")
    print(f"   docker exec -it oj-backend bash")
    print(f"4. 使用QDUOJ管理后台批量导入,或使用命令:")
    print(f"   cd /app && python manage.py import_problem /app/import_data")
    print("="*60)


if __name__ == '__main__':
    main()
