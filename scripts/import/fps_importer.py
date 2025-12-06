#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPS 题库导入工具
用于将 Free Problem Set (FPS) 格式的题目批量导入到 QDUOJ 系统

使用方法：
1. 下载 FPS 题库：https://github.com/zhblue/freeproblemset
2. 解压到本地目录
3. 运行此脚本：python fps_importer.py <fps_directory>
"""

import os
import sys
import json
import zipfile
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional


class FPSImporter:
    """FPS 题目导入器"""
    
    def __init__(self, oj_url: str, admin_username: str, admin_password: str):
        """
        初始化导入器
        
        Args:
            oj_url: OJ系统的URL，例如 http://localhost:8000
            admin_username: 管理员用户名
            admin_password: 管理员密码
        """
        self.oj_url = oj_url.rstrip('/')
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self) -> bool:
        """登录到OJ系统"""
        try:
            # 获取登录页面以获取CSRF token
            login_page = self.session.get(f"{self.oj_url}/admin/login/")
            if 'csrftoken' in self.session.cookies:
                self.csrf_token = self.session.cookies['csrftoken']
            
            # 执行登录
            login_data = {
                'username': self.admin_username,
                'password': self.admin_password,
                'csrfmiddlewaretoken': self.csrf_token
            }
            
            response = self.session.post(
                f"{self.oj_url}/api/admin/login",
                json=login_data,
                headers={'X-CSRFToken': self.csrf_token}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('error') is None:
                    print(f"✅ 登录成功：{self.admin_username}")
                    return True
            
            print(f"❌ 登录失败：{response.text}")
            return False
            
        except Exception as e:
            print(f"❌ 登录异常：{e}")
            return False
    
    def parse_fps_problem(self, fps_file: Path) -> Optional[Dict]:
        """
        解析FPS格式的题目文件
        
        Args:
            fps_file: FPS题目文件路径（.fps或.xml）
            
        Returns:
            解析后的题目数据字典
        """
        try:
            # FPS格式实际上是一个压缩包
            if not zipfile.is_zipfile(fps_file):
                print(f"⚠️  {fps_file.name} 不是有效的FPS文件")
                return None
            
            with zipfile.ZipFile(fps_file, 'r') as zip_ref:
                # 读取problem.json或problem.xml
                problem_data = None
                
                if 'problem.json' in zip_ref.namelist():
                    with zip_ref.open('problem.json') as f:
                        problem_data = json.load(f)
                elif 'problem.xml' in zip_ref.namelist():
                    # 如果是XML格式，需要解析XML
                    print(f"⚠️  {fps_file.name} 使用XML格式，建议转换为JSON格式")
                    return None
                
                if not problem_data:
                    print(f"⚠️  {fps_file.name} 中未找到题目数据")
                    return None
                
                # 提取测试数据
                test_cases = []
                for file_name in zip_ref.namelist():
                    if file_name.startswith('testdata/'):
                        # 读取输入输出文件
                        if file_name.endswith('.in'):
                            base_name = file_name.replace('.in', '')
                            out_file = base_name + '.out'
                            
                            if out_file in zip_ref.namelist():
                                with zip_ref.open(file_name) as f_in:
                                    input_data = f_in.read().decode('utf-8', errors='ignore')
                                with zip_ref.open(out_file) as f_out:
                                    output_data = f_out.read().decode('utf-8', errors='ignore')
                                
                                test_cases.append({
                                    'input': input_data,
                                    'output': output_data
                                })
                
                problem_data['test_cases'] = test_cases
                return problem_data
                
        except Exception as e:
            print(f"❌ 解析 {fps_file.name} 失败：{e}")
            return None
    
    def convert_to_qduoj_format(self, fps_data: Dict) -> Dict:
        """
        将FPS格式转换为QDUOJ格式
        
        Args:
            fps_data: FPS格式的题目数据
            
        Returns:
            QDUOJ格式的题目数据
        """
        # QDUOJ题目数据结构
        qduoj_problem = {
            'title': fps_data.get('title', 'Untitled'),
            'description': fps_data.get('description', ''),
            'input_description': fps_data.get('input', ''),
            'output_description': fps_data.get('output', ''),
            'time_limit': fps_data.get('time_limit', 1000),  # 毫秒
            'memory_limit': fps_data.get('memory_limit', 256),  # MB
            'difficulty': self._convert_difficulty(fps_data.get('difficulty', 'Low')),
            'tags': fps_data.get('tags', []),
            'hint': fps_data.get('hint', ''),
            'source': fps_data.get('source', 'FPS'),
            'samples': [],
            'test_case_score': [],
            'languages': ['C', 'C++', 'Java', 'Python2', 'Python3']
        }
        
        # 转换样例数据
        for sample in fps_data.get('samples', []):
            qduoj_problem['samples'].append({
                'input': sample.get('input', ''),
                'output': sample.get('output', '')
            })
        
        # 设置测试用例分数（平均分配）
        test_cases = fps_data.get('test_cases', [])
        if test_cases:
            score_per_case = 100 // len(test_cases)
            for i, _ in enumerate(test_cases):
                score = score_per_case
                # 最后一个测试用例补齐到100分
                if i == len(test_cases) - 1:
                    score = 100 - score_per_case * (len(test_cases) - 1)
                qduoj_problem['test_case_score'].append({
                    'input_name': f'{i+1}.in',
                    'output_name': f'{i+1}.out',
                    'score': score
                })
        
        return qduoj_problem
    
    def _convert_difficulty(self, fps_difficulty: str) -> str:
        """转换难度级别"""
        difficulty_map = {
            'Low': 'Low',
            'Mid': 'Mid',
            'High': 'High'
        }
        return difficulty_map.get(fps_difficulty, 'Low')
    
    def upload_test_cases(self, problem_id: str, test_cases: List[Dict]) -> bool:
        """
        上传测试用例
        
        Args:
            problem_id: 题目ID
            test_cases: 测试用例列表
            
        Returns:
            是否上传成功
        """
        try:
            # 创建测试数据压缩包
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
                with zipfile.ZipFile(tmp_path, 'w') as zip_ref:
                    for i, test_case in enumerate(test_cases, 1):
                        zip_ref.writestr(f'{i}.in', test_case['input'])
                        zip_ref.writestr(f'{i}.out', test_case['output'])
            
            # 上传测试数据
            with open(tmp_path, 'rb') as f:
                files = {'file': ('testdata.zip', f, 'application/zip')}
                response = self.session.post(
                    f"{self.oj_url}/api/admin/test_case",
                    files=files,
                    data={'problem_id': problem_id},
                    headers={'X-CSRFToken': self.csrf_token}
                )
            
            # 清理临时文件
            os.unlink(tmp_path)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('error') is None:
                    return True
            
            print(f"❌ 上传测试数据失败：{response.text}")
            return False
            
        except Exception as e:
            print(f"❌ 上传测试数据异常：{e}")
            return False
    
    def create_problem(self, problem_data: Dict, test_cases: List[Dict]) -> bool:
        """
        创建题目
        
        Args:
            problem_data: 题目数据
            test_cases: 测试用例
            
        Returns:
            是否创建成功
        """
        try:
            # 创建题目
            response = self.session.post(
                f"{self.oj_url}/api/admin/problem",
                json=problem_data,
                headers={'X-CSRFToken': self.csrf_token}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('error') is None:
                    problem_id = result['data']['id']
                    print(f"  ✅ 题目创建成功：ID={problem_id}")
                    
                    # 上传测试用例
                    if test_cases:
                        print(f"  📤 上传测试用例（{len(test_cases)}个）...")
                        if self.upload_test_cases(problem_id, test_cases):
                            print(f"  ✅ 测试用例上传成功")
                        else:
                            print(f"  ⚠️  测试用例上传失败")
                    
                    return True
            
            print(f"  ❌ 创建题目失败：{response.text}")
            return False
            
        except Exception as e:
            print(f"  ❌ 创建题目异常：{e}")
            return False
    
    def import_fps_directory(self, fps_dir: Path) -> Dict[str, int]:
        """
        导入FPS题库目录
        
        Args:
            fps_dir: FPS题库目录
            
        Returns:
            导入统计信息
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # 查找所有FPS文件
        fps_files = []
        for ext in ['*.fps', '*.zip']:
            fps_files.extend(fps_dir.glob(f'**/{ext}'))
        
        print(f"\n📚 发现 {len(fps_files)} 个题目文件")
        print("=" * 60)
        
        for fps_file in fps_files:
            stats['total'] += 1
            print(f"\n[{stats['total']}/{len(fps_files)}] 处理：{fps_file.name}")
            
            # 解析FPS文件
            fps_data = self.parse_fps_problem(fps_file)
            if not fps_data:
                stats['skipped'] += 1
                continue
            
            # 转换为QDUOJ格式
            qduoj_data = self.convert_to_qduoj_format(fps_data)
            test_cases = fps_data.get('test_cases', [])
            
            print(f"  📝 题目：{qduoj_data['title']}")
            print(f"  🏷️  难度：{qduoj_data['difficulty']}")
            print(f"  📊 测试用例：{len(test_cases)}个")
            
            # 创建题目
            if self.create_problem(qduoj_data, test_cases):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        return stats


def main():
    parser = argparse.ArgumentParser(description='FPS题库导入工具')
    parser.add_argument('fps_dir', type=str, help='FPS题库目录路径')
    parser.add_argument('--url', type=str, default='http://localhost:8000',
                        help='OJ系统URL (默认: http://localhost:8000)')
    parser.add_argument('--username', type=str, default='root',
                        help='管理员用户名 (默认: root)')
    parser.add_argument('--password', type=str, default='rootroot',
                        help='管理员密码 (默认: rootroot)')
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    fps_dir = Path(args.fps_dir)
    if not fps_dir.exists() or not fps_dir.is_dir():
        print(f"❌ 错误：目录不存在 {fps_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("FPS 题库导入工具")
    print("=" * 60)
    print(f"OJ系统：{args.url}")
    print(f"题库目录：{fps_dir}")
    print("=" * 60)
    
    # 创建导入器
    importer = FPSImporter(args.url, args.username, args.password)
    
    # 登录
    if not importer.login():
        print("❌ 登录失败，请检查用户名和密码")
        sys.exit(1)
    
    # 导入题库
    stats = importer.import_fps_directory(fps_dir)
    
    # 输出统计
    print("\n" + "=" * 60)
    print("📊 导入统计")
    print("=" * 60)
    print(f"总题目数：{stats['total']}")
    print(f"✅ 成功：{stats['success']}")
    print(f"❌ 失败：{stats['failed']}")
    print(f"⏭️  跳过：{stats['skipped']}")
    print(f"成功率：{stats['success']/stats['total']*100:.1f}%" if stats['total'] > 0 else "N/A")
    print("=" * 60)


if __name__ == '__main__':
    main()
