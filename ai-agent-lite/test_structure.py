"""
Quick test to verify supervisor pattern code structure without LLM calls
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.supervisor import Supervisor, AgentType, StudentState
from app.workers import CodeReviewerAgent, ProblemAnalyzerAgent, ContestCoachAgent, LearningPartnerAgent, LearningManagerAgent

def test_structure():
    """Test that all components can be instantiated and basic methods work."""
    
    print("🧪 Testing Supervisor Pattern Structure...")
    
    # Test state object
    state = StudentState()
    state.emotion_tags = {"frustration": 0.8}
    assert state.emotion_tags["frustration"] == 0.8
    print("✅ StudentState works")
    
    # Test agent types
    assert AgentType.CODE_REVIEWER.value == "code_reviewer"
    assert AgentType.LEARNING_PARTNER.value == "learning_partner"
    print("✅ AgentType enum works")
    
    # Test supervisor instantiation (without LLM)
    supervisor = Supervisor(None)
    assert supervisor is not None
    print("✅ Supervisor instantiation works")
    
    # Test intent classification logic (mocked)
    def mock_classify_intent(input_text):
        if "代码" in input_text or "优化" in input_text:
            return "code_review"
        elif "难" in input_text or "不会" in input_text:
            return "emotional_support"
        return "general_question"
    
    # Monkey patch for testing
    supervisor._classify_intent = lambda x: mock_classify_intent(x)
    
    # Test routing logic
    agent_type = supervisor._determine_agent("code_review", "测试代码")
    assert agent_type == AgentType.CODE_REVIEWER
    print("✅ Code review routing works")
    
    # Test emotional state override
    supervisor.state.emotion_tags = {"frustration": 0.9}
    agent_type = supervisor._determine_agent("code_review", "测试代码")
    assert agent_type == AgentType.LEARNING_PARTNER  # Should override due to high frustration
    print("✅ Emotional state override works")
    
    # Test worker instantiation
    workers = {
        AgentType.CODE_REVIEWER: CodeReviewerAgent(None),
        AgentType.PROBLEM_ANALYZER: ProblemAnalyzerAgent(None),
        AgentType.CONTEST_COACH: ContestCoachAgent(None),
        AgentType.LEARNING_PARTNER: LearningPartnerAgent(None),
        AgentType.LEARNING_MANAGER: LearningManagerAgent(None)
    }
    
    for agent_type, worker in workers.items():
        assert worker is not None
        print(f"✅ {agent_type.value} worker instantiation works")
    
    print("\n🎉 All structure tests passed! Supervisor pattern is correctly implemented.")
    print("\nNext steps:")
    print("1. Test with actual LLM calls (may require API key)")
    print("2. Verify WebSocket integration")
    print("3. Test state persistence")

if __name__ == "__main__":
    test_structure()