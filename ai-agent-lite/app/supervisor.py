"""
Supervisor Agent - Central router for multi-agent orchestration
Based on student state and intent to dispatch to specialized workers.
"""
from enum import Enum
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("ai-agent-lite.supervisor")

class AgentType(Enum):
    CODE_REVIEWER = "code_reviewer"
    PROBLEM_ANALYZER = "problem_analyzer" 
    CONTEST_COACH = "contest_coach"
    LEARNING_PARTNER = "learning_partner"
    LEARNING_MANAGER = "learning_manager"

@dataclass
class StudentState:
    # Core learning state
    current_problem_id: Optional[str] = None
    submitted_code: Optional[str] = None
    knowledge_graph_position: Dict[str, float] = None  # {topic: mastery_level}
    
    # Emotional state
    emotion_tags: Dict[str, float] = None  # {"frustration": 0.7, "excitement": 0.3}
    efficiency_trend: float = 1.0  # Relative to baseline
    
    # Temporal context
    session_start_time: datetime = None
    last_activity_time: datetime = None
    
    def __post_init__(self):
        if self.knowledge_graph_position is None:
            self.knowledge_graph_position = {}
        if self.emotion_tags is None:
            self.emotion_tags = {}

class Supervisor:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.state = StudentState()
        
    async def route_request(self, user_input: str, session_context: Dict[str, Any]) -> AgentType:
        """Determine which agent should handle this request based on intent and state."""
        
        # Update state from context
        self._update_state_from_context(session_context)
        
        # Intent classification with LLM
        intent = await self._classify_intent(user_input)
        
        # State-aware routing logic
        agent_type = self._determine_agent(intent, user_input)
        
        logger.info(f"Supervisor routing: intent={intent}, agent={agent_type}")
        return agent_type
    
    async def _classify_intent(self, user_input: str) -> str:
        """Use LLM to classify user intent."""
        prompt = f"""
        请根据学生的输入判断其意图（编程竞赛培训场景）：

        输入："{user_input}"

        可能的意图：
        - code_review：请求代码分析、优化或风格点评
        - problem_help：需要帮助理解或解决题目
        - contest_prep：寻求竞赛策略或压力模拟
        - emotional_support：表达挫折、困惑或需要鼓励
        - learning_plan：请求学习建议或进度跟踪
        - general_question：其他算法/数据结构问题

        仅返回意图名称。
        """
        
        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return response.strip().lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "general_question"
    
    def _determine_agent(self, intent: str, user_input: str) -> AgentType:
        """State-aware agent selection."""
        
        # Emotional state override - always prioritize emotional support
        if self._needs_emotional_support():
            return AgentType.LEARNING_PARTNER
            
        # Performance-based routing
        if self._needs_difficulty_adjustment():
            return AgentType.LEARNING_MANAGER
        
        # Intent-based routing
        intent_mapping = {
            "code_review": AgentType.CODE_REVIEWER,
            "problem_help": AgentType.PROBLEM_ANALYZER,
            "contest_prep": AgentType.CONTEST_COACH,
            "emotional_support": AgentType.LEARNING_PARTNER,
            "learning_plan": AgentType.LEARNING_MANAGER,
            "general_question": AgentType.PROBLEM_ANALYZER
        }
        
        return intent_mapping.get(intent, AgentType.PROBLEM_ANALYZER)
    
    def _needs_emotional_support(self) -> bool:
        """Check if student needs emotional support based on state."""
        frustration = self.state.emotion_tags.get("frustration", 0)
        confusion = self.state.emotion_tags.get("confusion", 0)
        return frustration > 0.6 or confusion > 0.7
    
    def _needs_difficulty_adjustment(self) -> bool:
        """Check if learning difficulty needs adjustment."""
        return self.state.efficiency_trend < 0.7  # 30% efficiency drop
    
    def _update_state_from_context(self, context: Dict[str, Any]):
        """Update state from session context."""
        if "problem_id" in context:
            self.state.current_problem_id = context["problem_id"]
        if "submitted_code" in context:
            self.state.submitted_code = context["submitted_code"]
        # Update emotional state based on message tone
        self._analyze_emotional_state(context.get("message_history", []))
    
    def _analyze_emotional_state(self, message_history: list):
        """Simple emotional state analysis from message history."""
        # This would be enhanced with proper sentiment analysis
        recent_messages = message_history[-3:] if message_history else []
        
        emotional_indicators = {
            "frustration": ["难", "不会", "崩溃", "frustrat", "hard", "can't"],
            "excitement": ["太好", "明白了", "excit", "great", "understand"],
            "confusion": ["为什么", "不懂", "confus", "why", "don't understand"]
        }
        
        for emotion, indicators in emotional_indicators.items():
            count = sum(1 for msg in recent_messages 
                       if any(indicator in msg.get('content', '').lower() 
                            for indicator in indicators))
            self.state.emotion_tags[emotion] = min(1.0, count * 0.3)

# Test hot reload comment
# Hot reload test comment
