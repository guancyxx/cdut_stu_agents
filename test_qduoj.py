"""
QDUOJ 快速测试脚本
测试 QDUOJ API 的基本功能
"""

import requests
import json
from datetime import datetime


def test_qduoj():
    """测试 QDUOJ 基本功能"""
    
    base_url = "http://localhost"
    print("="*60)
    print("QDUOJ API 测试")
    print("="*60)
    
    # 1. 测试首页
    print("\n[1] 测试首页访问...")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ 首页访问成功")
        else:
            print(f"❌ 首页返回状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}")
        return
    
    # 2. 测试 API 基础访问
    print("\n[2] 测试 API 基础访问...")
    try:
        response = requests.get(f"{base_url}/api/website", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ API 访问成功")
            if 'data' in data:
                website_info = data['data']
                print(f"   网站名称: {website_info.get('website_name', 'N/A')}")
        else:
            print(f"❌ API 返回状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ API 访问失败: {e}")
    
    # 3. 测试登录
    print("\n[3] 测试管理员登录...")
    session = requests.Session()
    login_data = {
        "username": "root",
        "password": "rootroot"
    }
    
    try:
        response = session.post(f"{base_url}/api/login", json=login_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('error') is None:
                print("✅ 登录成功")
                user_data = result.get('data', {})
                print(f"   用户: {user_data.get('username', 'N/A')}")
                print(f"   角色: {'管理员' if user_data.get('admin_type') else '普通用户'}")
            else:
                print(f"❌ 登录失败: {result.get('data', 'Unknown error')}")
                return
        else:
            print(f"❌ 登录请求失败，状态码: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return
    
    # 4. 测试获取题目列表
    print("\n[4] 测试获取题目列表...")
    try:
        response = session.get(f"{base_url}/api/problem/?limit=5", timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('error') is None:
                problems = result['data']
                print(f"✅ 题目列表获取成功")
                print(f"   总题目数: {problems['total']}")
                
                if problems['results']:
                    print("\n   前几道题目:")
                    for idx, problem in enumerate(problems['results'][:3], 1):
                        print(f"   {idx}. [{problem['_id']}] {problem['title']}")
                        print(f"      难度: {problem.get('difficulty', 'N/A')}")
                        print(f"      提交数: {problem.get('submission_number', 0)}")
                        print(f"      通过数: {problem.get('accepted_number', 0)}")
                else:
                    print("   ⚠️ 暂无题目，请在管理后台创建或导入题目")
            else:
                print(f"❌ 获取题目失败: {result.get('data', 'Unknown error')}")
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取题目列表失败: {e}")
    
    # 5. 测试获取竞赛列表
    print("\n[5] 测试获取竞赛列表...")
    try:
        response = session.get(f"{base_url}/api/contests/?limit=5", timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('error') is None:
                contests = result['data']
                print(f"✅ 竞赛列表获取成功")
                print(f"   总竞赛数: {contests['total']}")
                
                if contests['results']:
                    print("\n   竞赛列表:")
                    for idx, contest in enumerate(contests['results'][:3], 1):
                        print(f"   {idx}. {contest['title']}")
                        print(f"      状态: {contest.get('status', 'N/A')}")
                else:
                    print("   暂无竞赛")
            else:
                print(f"❌ 获取竞赛失败: {result.get('data', 'Unknown error')}")
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取竞赛列表失败: {e}")
    
    # 6. 测试判题服务器状态
    print("\n[6] 测试判题服务器状态...")
    try:
        response = session.get(f"{base_url}/api/admin/judge_server", timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('error') is None:
                servers = result['data']
                print(f"✅ 判题服务器状态获取成功")
                print(f"   服务器数量: {len(servers)}")
                
                if servers:
                    for idx, server in enumerate(servers, 1):
                        print(f"\n   服务器 {idx}:")
                        print(f"      状态: {'正常' if server.get('status') == 'normal' else '异常'}")
                        print(f"      CPU 使用: {server.get('cpu_usage', 0):.1f}%")
                        print(f"      内存使用: {server.get('memory_usage', 0):.1f}%")
                else:
                    print("   ⚠️ 未检测到判题服务器")
            else:
                print(f"❌ 获取判题服务器状态失败: {result.get('data', 'Unknown error')}")
        else:
            print(f"⚠️ 无法获取判题服务器状态（可能需要管理员权限）")
    except Exception as e:
        print(f"⚠️ 获取判题服务器状态失败: {e}")
    
    # 总结
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)
    print("\n📝 后续操作建议:")
    print("1. 访问 http://localhost 查看 Web 界面")
    print("2. 访问 http://localhost/admin 进入管理后台")
    print("3. 修改管理员密码（用户名: root, 密码: rootroot）")
    print("4. 在管理后台创建或导入题目")
    print("5. 使用 custom_agents/tools/qduoj_client.py 进行 API 集成")
    print("\n")


if __name__ == "__main__":
    test_qduoj()
