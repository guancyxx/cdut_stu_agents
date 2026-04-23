"""
Specialized Worker Agents for programming competition training.
Each agent focuses on a specific aspect of student development.
"""
from enum import Enum
from typing import Dict, Any, List
import logging
from dataclasses import dataclass

logger = logging.getLogger("ai-agent-lite.workers")

class CompletionStatus(Enum):
    COMPLETE = "complete"
    NEEDS_FOLLOWUP = "needs_followup"
    ERROR = "error"

@dataclass 
class AgentResponse:
    content: str
    status: CompletionStatus
    metadata: Dict[str, Any] = None
    next_actions: List[Dict] = None

class BaseWorker:
    """Base class for all specialized workers."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        """Process user input and return structured response."""
        raise NotImplementedError

class CodeReviewerAgent(BaseWorker):
    """Specialized in code quality, efficiency, and style evaluation."""
    
    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        code = state.get("submitted_code", "")
        language = state.get("language", "unknown")
        
        prompt = f"""
        As an expert code reviewer for programming competitions, analyze this {language} code:
        
        Code:
        ```{language}
        {code}
        ```
        
        Student's question: {user_input}
        
        Provide structured analysis covering:
        1. Logic Correctness (✅/⚠️/❌ + brief explanation)
        2. Time Complexity Analysis (Big O notation)  
        3. Space Complexity Analysis
        4. Code Style Assessment (naming, structure, readability)
        5. 3 Specific Improvement Suggestions
        6. Related Algorithm/Data Structure to review
        
        Format response clearly with sections.
        """
        
        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"analysis_type": "code_review", "language": language}
            )
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return AgentResponse(
                content="Code analysis temporarily unavailable.",
                status=CompletionStatus.ERROR
            )

class ProblemAnalyzerAgent(BaseWorker):
    """Deep analysis of competition problems and solution guidance."""
    
    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        problem_id = state.get("current_problem_id", "unknown")
        
        prompt = f"""
        As a programming competition problem expert, help with problem analysis:
        
        Problem Context: {problem_id}
        Student's Question: {user_input}
        
        Provide comprehensive guidance covering:
        1. Problem Understanding (what is being asked)
        2. Solution Approach (step-by-step strategy)
        3. Algorithm Selection (optimal choices and alternatives)
        4. Edge Cases to consider
        5. Implementation Tips
        6. Related Problems for practice
        
        Focus on teaching problem-solving thinking, not just giving answers.
        """
        
        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"problem_id": problem_id, "analysis_depth": "detailed"}
            )
        except Exception as e:
            logger.error(f"Problem analysis failed: {e}")
            return AgentResponse(
                content="Problem analysis temporarily unavailable.",
                status=CompletionStatus.ERROR
            )

class ContestCoachAgent(BaseWorker):
    """Simulates competition pressure and provides strategic advice."""
    
    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        prompt = f"""
        As a programming competition coach, provide strategic advice:
        
        Student's Situation: {user_input}
        
        Focus on competition-specific guidance:
        1. Time Management Strategies
        2. Problem Selection Priority (easy/medium/hard)
        3. Debugging under Pressure
        4. Common Competition Pitfalls to Avoid
        5. Mental Preparation Techniques
        6. Mock Competition Scenarios
        
        Use competitive but supportive tone.
        """
        
        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"coaching_type": "contest_strategy"}
            )
        except Exception as e:
            logger.error(f"Contest coaching failed: {e}")
            return AgentResponse(
                content="Competition coaching temporarily unavailable.",
                status=CompletionStatus.ERROR
            )

class LearningPartnerAgent(BaseWorker):
    """Provides emotional support and motivation."""
    
    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        emotional_state = state.get("emotion_tags", {})
        
        prompt = f"""
        As a supportive learning partner, provide emotional support:
        
        Student's Expression: {user_input}
        Detected Emotional State: {emotional_state}
        
        Provide:
        1. Empathetic acknowledgement of feelings
        2. Encouragement and motivation  
        3. Growth mindset perspective
        4. Practical coping strategies
        5. Positive reinforcement of progress
        6. Gentle guidance back to learning
        
        Be warm, understanding, and genuinely supportive.
        """
        
        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"support_type": "emotional", "emotional_state": emotional_state}
            )
        except Exception as e:
            logger.error(f"Learning partner response failed: {e}")
            return AgentResponse(
                content="I'm here to support you. Let's continue learning together.",
                status=CompletionStatus.COMPLETE
            )

class LearningManagerAgent(BaseWorker):
    """Tracks progress and designs adaptive learning paths."""
    
    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        knowledge_graph = state.get("knowledge_graph_position", {})
        efficiency = state.get("efficiency_trend", 1.0)
        
        prompt = f"""
        As a learning manager, create personalized learning plan:
        
        Current Knowledge State: {knowledge_graph}
        Learning Efficiency: {efficiency}
        Student's Request: {user_input}
        
        Provide structured learning guidance:
        1. Current Skill Assessment
        2. Recommended Learning Objectives  
        3. Adaptive Difficulty Adjustment
        4. Practice Problem Recommendations
        5. Study Schedule Suggestions
        6. Progress Tracking Method
        
        Base recommendations on actual competency levels.
        """
        
        try:
            response = await self.llm.complete([{"role": "user", "content": prompt}])
            return AgentResponse(
                content=response,
                status=CompletionStatus.COMPLETE,
                metadata={"plan_type": "adaptive_learning", "efficiency_factor": efficiency}
            )
        except Exception as e:
            logger.error(f"Learning management failed: {e}")
            return AgentResponse(
                content="Learning planning temporarily unavailable.",
                status=CompletionStatus.ERROR
            )