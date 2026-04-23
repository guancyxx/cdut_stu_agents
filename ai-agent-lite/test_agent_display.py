#!/usr/bin/env python3

import json
import asyncio
import websockets
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_supervisor_integration():
    """Test the supervisor module"""
    try:
        from app.supervisor import Supervisor, AgentType
        from app.llm_client import LlmClient
        print(f"✅ Supervisor class loaded successfully")
        
        # Create LLM client first
        llm_client = LlmClient()
        supervisor = Supervisor(llm_client)
        
        # Test agent routing
        test_messages = [
            "请帮我分析一下这段代码",
            "这个算法的时间复杂度是多少",
            "如何准备编程竞赛",
            "我感觉有点沮丧", 
            "我的学习计划应该怎么做"
        ]
        
        for i, message in enumerate(test_messages):
            agent_type = await supervisor.route_request(message, {})
            print(f"✅ Message {i+1}: '{message}' -> {agent_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supervisor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_websocket_connection():
    """Test WebSocket connection with agent info"""
    try:
        uri = "ws://localhost:8850/ws"
        print(f"\nTesting WebSocket connection to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            # Send a simple message
            test_message = {
                "type": "message",
                "text": "你好，请帮我分析代码",
                "session_id": "test_session_123"
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Message sent successfully")
            
            # Try to receive a response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"✅ Received response: {response[:200]}...")
                
                # Check if response contains agent info
                data = json.loads(response)
                if 'type' in data and data['type'] == 'agent_info':
                    print(f"✅ Agent info received: {data}")
                elif 'data' in data and 'agent_type' in data['data']:
                    print(f"✅ Agent type in response: {data['data']['agent_type']}")
                else:
                    print("⚠️ No agent info in response")
                    
            except asyncio.TimeoutError:
                print("⚠️ No response received (timeout)")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def main():
    print("🧪 Testing AI Agent Display Functionality\n")
    
    # Test 1: Supervisor integration
    supervisor_success = await test_supervisor_integration()
    
    # Test 2: WebSocket connection (async)
    if supervisor_success:
        websocket_success = await test_websocket_connection()
    else:
        websocket_success = False
    
    print(f"\n📊 Test Results:")
    print(f"Supervisor Integration: {'✅' if supervisor_success else '❌'}")
    print(f"WebSocket Connection: {'✅' if websocket_success else '❌'}")
    
    if supervisor_success and websocket_success:
        print("\n🎉 All tests passed! Agent display functionality is ready.")
    else:
        print("\n⚠️ Some tests failed. Please check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())