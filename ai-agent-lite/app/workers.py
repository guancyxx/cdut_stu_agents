"""
Specialized Worker Agents for programming competition training.
Each agent focuses on a specific aspect of student development.
All prompts are in Chinese — Chinese is the sole interaction language.
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
        你是编程竞赛代码审查专家，请用中文分析以下 {language} 代码：
        
        代码：
        ```{language}
        {code}
        ```
        
        学生的问题：{user_input}
        
        请按以下结构进行分析：
        1. 逻辑正确性（✅/⚠️/❌ + 简要说明）
        2. 时间复杂度分析（大O表示法）
        3. 空间复杂度分析
        4. 代码风格评估（命名、结构、可读性）
        5. 3 条具体改进建议
        6. 相关算法/数据结构推荐
        
        请用中文清晰作答，分节格式输出。
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
        你是编程竞赛题目解析专家，请用中文帮助学生分析题目：
        
        题目上下文：{problem_id}
        学生的问题：{user_input}
        
        请提供以下指导：
        1. 题目理解（题目到底在问什么）
        2. 解题思路（分步骤策略）
        3. 算法选择（最优选择及替代方案）
        4. 边界情况考虑
        5. 实现技巧
        6. 相关练习题推荐
        
        重点培养解题思维，而非直接给出答案。
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
        你是编程竞赛教练，请用中文提供竞赛策略建议：
        
        学生的情况：{user_input}
        
        请提供以下竞赛专项指导：
        1. 时间管理策略
        2. 题目选择优先级（简单/中等/困难）
        3. 压力下调试技巧
        4. 常见竞赛陷阱及规避方法
        5. 心理准备技巧
        6. 模拟赛情景建议
        
        请用竞技但有鼓励性的语气作答。
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
        你是温暖的学习伙伴，请用中文提供情感支持和鼓励：
        
        学生的表达：{user_input}
        检测到的情绪状态：{emotional_state}
        
        请提供以下支持：
        1. 对学生感受的共情认同
        2. 鼓励和激励
        3. 成长型思维引导
        4. 实用的应对策略
        5. 对进步的积极肯定
        6. 温和地将学生引回学习中
        
        请保持温暖、理解和真诚支持的态度。
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
        你是学习管理专家，请用中文制定个性化学习计划：
        
        当前知识状态：{knowledge_graph}
        学习效率：{efficiency}
        学生请求：{user_input}
        
        请提供以下结构化学习指导：
        1. 当前技能评估
        2. 推荐学习目标
        3. 自适应难度调整建议
        4. 练习题推荐
        5. 学习计划建议
        6. 进度追踪方法
        
        请基于实际能力水平做出推荐。
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