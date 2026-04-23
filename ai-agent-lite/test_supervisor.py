"""
Test script for Supervisor pattern implementation
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.supervisor import Supervisor, AgentType
from app.workers import CodeReviewerAgent, ProblemAnalyzerAgent, ContestCoachAgent, LearningPartnerAgent, LearningManagerAgent
from app.llm_client import LlmClient

async def test_supervisor_pattern():
    """Test the supervisor pattern with different input types."""
    
    print("🧪 Testing Supervisor Pattern...")
    
    # Initialize components
    llm = LlmClient()
    supervisor = Supervisor(llm)
    
    workers = {
        AgentType.CODE_REVIEWER: CodeReviewerAgent(llm),
        AgentType.PROBLEM_ANALYZER: ProblemAnalyzerAgent(llm),
        AgentType.CONTEST_COACH: ContestCoachAgent(llm),
        AgentType.LEARNING_PARTNER: LearningPartnerAgent(llm),
        AgentType.LEARNING_MANAGER: LearningManagerAgent(llm)
    }
    
    # Test cases
    test_cases = [
        {
            "input": "帮我看看这段代码哪里可以优化？",
            "expected_agent": AgentType.CODE_REVIEWER,
            "description": "Code review request"
        },
        {
            "input": "这道动态规划的题不会做，能教教我吗？", 
            "expected_agent": AgentType.PROBLEM_ANALYZER,
            "description": "Problem solving help"
        },
        {
            "input": "比赛时总是紧张，有什么建议？",
            "expected_agent": AgentType.CONTEST_COACH,
            "description": "Competition stress"
        },
        {
            "input": "学不下去了，好难啊",
            "expected_agent": AgentType.LEARNING_PARTNER,
            "description": "Emotional support needed"
        },
        {
            "input": "接下来我应该学什么？",
            "expected_agent": AgentType.LEARNING_MANAGER,
            "description": "Learning plan request"
        }
    ]
    
    print(f"\n📋 Running {len(test_cases)} test cases...")
    
    passed = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        print(f"Input: {test_case['input']}")
        
        try:
            # Test routing
            agent_type = await supervisor.route_request(test_case['input'], {})
            print(f"Selected Agent: {agent_type.value}")
            print(f"Expected Agent: {test_case['expected_agent'].value}")
            
            if agent_type == test_case['expected_agent']:
                print("✅ PASS - Correct agent selected")
                passed += 1
                
                # Test worker processing
                worker = workers[agent_type]
                response = await worker.process(test_case['input'], {
                    "current_problem_id": "test-problem-123",
                    "submitted_code": "def example():\n    pass" if agent_type == AgentType.CODE_REVIEWER else ""
                })
                
                print(f"Worker Response Length: {len(response.content)} chars")
                print(f"Status: {response.status.value}")
                
            else:
                print("❌ FAIL - Wrong agent selected")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n📊 Results: {passed}/{len(test_cases)} tests passed")
    
    if passed == len(test_cases):
        print("🎉 All tests passed! Supervisor pattern is working correctly.")
    else:
        print("⚠️  Some tests failed. Check implementation.")

if __name__ == "__main__":
    asyncio.run(test_supervisor_pattern())