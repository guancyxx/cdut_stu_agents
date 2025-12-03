"""
QDUOJ API 集成工具
用于与 QDUOJ 系统进行交互
"""

import requests
from typing import Dict, List, Optional
import json


class QDUOJClient:
    """QDUOJ API 客户端"""
    
    def __init__(self, base_url: str = "http://oj-backend:8000", token: str = None):
        """
        初始化 QDUOJ 客户端
        
        Args:
            base_url: QDUOJ 后端 API 地址
            token: 用户认证 token（登录后获取）
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.token = token
        self.session = requests.Session()
        
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
    
    # ==================== 用户认证 ====================
    
    def login(self, username: str, password: str) -> Dict:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            包含 token 的用户信息
        """
        response = self.session.post(
            f"{self.api_url}/login",
            json={
                'username': username,
                'password': password
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get('error') is None:
            self.token = data['data']['token']
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
        
        return data
    
    def get_user_profile(self) -> Dict:
        """获取当前用户信息"""
        response = self.session.get(f"{self.api_url}/profile")
        response.raise_for_status()
        return response.json()
    
    # ==================== 题目管理 ====================
    
    def get_problem_list(self, 
                        page: int = 1, 
                        limit: int = 20,
                        keyword: str = None,
                        difficulty: str = None,
                        tag: str = None) -> Dict:
        """
        获取题目列表
        
        Args:
            page: 页码
            limit: 每页数量
            keyword: 搜索关键词
            difficulty: 难度 (Low/Mid/High)
            tag: 标签
            
        Returns:
            题目列表数据
        """
        params = {
            'page': page,
            'limit': limit,
            'offset': (page - 1) * limit
        }
        
        if keyword:
            params['keyword'] = keyword
        if difficulty:
            params['difficulty'] = difficulty
        if tag:
            params['tag'] = tag
        
        response = self.session.get(
            f"{self.api_url}/problem",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_problem_detail(self, problem_id: int) -> Dict:
        """
        获取题目详情
        
        Args:
            problem_id: 题目 ID
            
        Returns:
            题目详细信息
        """
        response = self.session.get(f"{self.api_url}/problem/{problem_id}")
        response.raise_for_status()
        return response.json()
    
    # ==================== 代码提交 ====================
    
    def submit_code(self,
                   problem_id: int,
                   language: str,
                   code: str,
                   contest_id: Optional[int] = None) -> Dict:
        """
        提交代码
        
        Args:
            problem_id: 题目 ID
            language: 编程语言 (C, C++, Java, Python2, Python3, etc.)
            code: 代码内容
            contest_id: 竞赛 ID（可选，如果是竞赛题目）
            
        Returns:
            提交结果
        """
        data = {
            'problem_id': problem_id,
            'language': language,
            'code': code
        }
        
        if contest_id:
            data['contest_id'] = contest_id
        
        response = self.session.post(
            f"{self.api_url}/submission",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_submission_detail(self, submission_id: str) -> Dict:
        """
        获取提交详情
        
        Args:
            submission_id: 提交 ID
            
        Returns:
            提交详细信息（包括判题结果）
        """
        response = self.session.get(f"{self.api_url}/submission/{submission_id}")
        response.raise_for_status()
        return response.json()
    
    def get_submission_list(self,
                           problem_id: Optional[int] = None,
                           myself: bool = False,
                           result: Optional[int] = None,
                           page: int = 1,
                           limit: int = 20) -> Dict:
        """
        获取提交列表
        
        Args:
            problem_id: 题目 ID（可选）
            myself: 是否只看自己的提交
            result: 判题结果筛选
            page: 页码
            limit: 每页数量
            
        Returns:
            提交记录列表
        """
        params = {
            'page': page,
            'limit': limit,
            'offset': (page - 1) * limit
        }
        
        if problem_id:
            params['problem_id'] = problem_id
        if myself:
            params['myself'] = 1
        if result is not None:
            params['result'] = result
        
        response = self.session.get(
            f"{self.api_url}/submissions",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== 竞赛管理 ====================
    
    def get_contest_list(self, page: int = 1, limit: int = 20) -> Dict:
        """获取竞赛列表"""
        params = {
            'page': page,
            'limit': limit,
            'offset': (page - 1) * limit
        }
        
        response = self.session.get(
            f"{self.api_url}/contests",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_contest_detail(self, contest_id: int) -> Dict:
        """获取竞赛详情"""
        response = self.session.get(f"{self.api_url}/contest/{contest_id}")
        response.raise_for_status()
        return response.json()
    
    # ==================== 排行榜 ====================
    
    def get_ranklist(self, page: int = 1, limit: int = 20) -> Dict:
        """获取总排行榜"""
        params = {
            'page': page,
            'limit': limit,
            'offset': (page - 1) * limit
        }
        
        response = self.session.get(
            f"{self.api_url}/user_rank",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_contest_ranklist(self, contest_id: int) -> Dict:
        """获取竞赛排行榜"""
        response = self.session.get(f"{self.api_url}/contest_rank/{contest_id}")
        response.raise_for_status()
        return response.json()


# ==================== 辅助函数 ====================

def parse_judge_result(result_code: int) -> str:
    """
    解析判题结果代码
    
    Args:
        result_code: 判题结果代码
        
    Returns:
        判题结果描述
    """
    results = {
        -2: "编译中",
        -1: "判题失败",
        0: "待判题",
        1: "判题中",
        2: "正在编译",
        3: "编译错误",
        4: "答案正确 (Accepted)",
        5: "格式错误",
        6: "答案错误",
        7: "超时",
        8: "内存超限",
        9: "运行错误",
        10: "系统错误"
    }
    return results.get(result_code, "未知结果")


def get_language_code(language_name: str) -> str:
    """
    获取语言代码
    
    Args:
        language_name: 语言名称
        
    Returns:
        标准语言代码
    """
    language_map = {
        'c': 'C',
        'c++': 'C++',
        'cpp': 'C++',
        'java': 'Java',
        'python': 'Python3',
        'python3': 'Python3',
        'python2': 'Python2',
        'go': 'Go',
        'javascript': 'JavaScript',
        'rust': 'Rust'
    }
    return language_map.get(language_name.lower(), 'C++')


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化客户端
    client = QDUOJClient(base_url="http://localhost:8000")
    
    # 登录
    login_result = client.login("admin", "admin123456")
    print("登录结果:", login_result)
    
    # 获取题目列表
    problems = client.get_problem_list(limit=10)
    print(f"\n题目列表 (共 {problems['data']['total']} 题):")
    for problem in problems['data']['results']:
        print(f"  - [{problem['_id']}] {problem['title']} (难度: {problem['difficulty']})")
    
    # 获取题目详情
    if problems['data']['results']:
        problem_id = problems['data']['results'][0]['_id']
        problem_detail = client.get_problem_detail(problem_id)
        print(f"\n题目详情: {problem_detail['data']['title']}")
        print(f"描述: {problem_detail['data']['description'][:100]}...")
    
    # 提交代码示例
    code = """
#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}
    """
    
    # submission = client.submit_code(
    #     problem_id=1,
    #     language='C++',
    #     code=code
    # )
    # print("\n提交结果:", submission)
