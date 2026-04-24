"""
Specialized Worker Agents for programming competition training.
Each agent focuses on a specific aspect of student development.
All AI responses to users must be in Chinese (简体中文).
Prompts and code remain in English only.
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
        1. Logic Correctness (checkmark/warning/cross + brief explanation)
        2. Time Complexity Analysis (Big O notation)  
        3. Space Complexity Analysis
        4. Code Style Assessment (naming, structure, readability)
        5. 3 Specific Improvement Suggestions
        
        Format response clearly with sections.
        IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
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
        
        Focus on teaching problem-solving thinking, not just giving answers.
        IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
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
        
        Use competitive but supportive tone.
        IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
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
        
        Be warm, understanding, and genuinely supportive.
        IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
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

class NextStepSuggester(BaseWorker):
    """Generates contextual next-step suggestions at the end of a conversation turn.

    This agent runs ONLY after the primary worker has finished producing content.
    It does not generate message content — it returns structured suggestion items
    that the WebSocket handler sends as a separate `next_suggestions` event.
    Suggestion titles and reasons are in Chinese for user-facing display.

    The prompt is driven by state_delta (knowledge_graph_position diff) rather than
    a generic summary of the agent response, producing targeted next actions.
    """

    SUGGESTION_TYPES = ("practice", "learn", "review", "debug", "compete")

    async def suggest(
        self,
        user_input: str,
        agent_response: str,
        agent_type: str,
        state: Dict[str, Any],
        state_delta: Dict[str, Any] = None,
    ) -> List[Dict[str, str]]:
        """Return 2-3 structured next-step suggestions based on state delta.

        If state_delta is provided and contains meaningful changes, the prompt
        focuses on those specific knowledge gains/gaps.  If no delta or empty
        delta, falls back to a context-only prompt.

        Returns a list of dicts with keys: type, title, target, reason.
        On failure returns an empty list (never raises).
        """
        # Build delta-human-readable section
        delta_section = ""
        if state_delta:
            gained = state_delta.get("gained", {})
            improved = state_delta.get("improved", {})
            weakened = state_delta.get("weakened", {})
            stable_topics = state_delta.get("stable", {})
            before_summary = state_delta.get("before_summary", {})
            after_summary = state_delta.get("after_summary", {})

            delta_lines = []
            if gained:
                items = ", ".join(f"{k}({v})" for k, v in gained.items())
                delta_lines.append(f"新掌握: {items}")
            if improved:
                items = ", ".join(
                    f"{k}: {v['before']}→{v['after']}" for k, v in improved.items()
                )
                delta_lines.append(f"进步: {items}")
            if weakened:
                items = ", ".join(
                    f"{k}: {v['before']}→{v['after']}" for k, v in weakened.items()
                )
                delta_lines.append(f"退步: {items}")
            if delta_lines:
                delta_section = "\n".join(delta_lines)
            elif stable_topics:
                # No meaningful change — suggest something new
                stable_list = ", ".join(f"{k}({v})" for k, v in stable_topics.items())
                delta_section = f"已掌握(无明显变化): {stable_list}"

        if delta_section:
            prompt = (
                "You are an AI programming-competition coach. Based on the student's "
                "knowledge state change this turn, suggest 2-3 concrete next actions "
                "that directly build on their new capabilities or address weaknesses.\n\n"
                f"Student asked: {user_input}\n"
                f"Agent type: {agent_type}\n"
                f"Current problem: {state.get('current_problem_id', 'N/A')}\n"
                f"Knowledge change this turn:\n{delta_section}\n\n"
                "Rules:\n"
                "- Target the SPECIFIC topics that just improved or appeared (gained/improved).\n"
                "- If topics weakened, suggest review/debug on those exact topics.\n"
                "- If no meaningful change, suggest a NEW related topic to explore.\n"
                "- DO NOT suggest vague general actions.\n"
                '- Return JSON ONLY — no markdown, no explanation. Format:\n'
                '{"suggestions":[{"type":"practice|learn|review|debug|compete",'
                '"title":"short action title in Chinese (简体中文)",'
                '"target":"specific target or problem id",'
                '"reason":"why this helps — refer to the specific knowledge change, in Chinese (简体中文)"}]}\n'
                "Keep titles under 20 characters. Keep reasons under 40 characters. "
                "Title and reason MUST be in Chinese (简体中文)."
            )
        else:
            # Fallback: no delta available
            prompt = (
                "You are an AI programming-competition coach. Based on the conversation "
                "below, suggest 2-3 concrete next actions the student could take.\n\n"
                f"Student's last message: {user_input}\n"
                f"AI agent role: {agent_type}\n"
                f"AI response summary: {agent_response[:600]}\n"
                f"Current context: problem_id={state.get('current_problem_id', 'N/A')}\n\n"
                'Return JSON ONLY — no markdown, no explanation. Format:\n'
                '{"suggestions":[{"type":"practice|learn|review|debug|compete",'
                '"title":"short action title in Chinese (简体中文)",'
                '"target":"specific target or problem id",'
                '"reason":"why this helps, in Chinese (简体中文)"}]}\n'
                "Keep titles under 20 characters. Keep reasons under 40 characters. "
                "Title and reason MUST be in Chinese (简体中文)."
            )

        try:
            raw = await self.llm.complete([{"role": "user", "content": prompt}])
            import json as _json

            # Strip markdown fences if the model wraps them
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = _json.loads(cleaned)
            items = data.get("suggestions", [])
            validated = []
            for item in items[:3]:
                if not isinstance(item, dict):
                    continue
                validated.append({
                    "type": item.get("type", "learn") if item.get("type") in self.SUGGESTION_TYPES else "learn",
                    "title": str(item.get("title", ""))[:40],
                    "target": str(item.get("target", ""))[:60],
                    "reason": str(item.get("reason", ""))[:80],
                })
            return validated[:3]
        except Exception as exc:
            logger.warning("NextStepSuggester failed: %s", exc)
            return []

    async def process(self, user_input: str, state: Dict[str, Any]) -> AgentResponse:
        """Not used directly — ``suggest`` is the public interface."""
        return AgentResponse(
            content="",
            status=CompletionStatus.COMPLETE,
            metadata={"role": "next_step_suggester"},
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
        
        Base recommendations on actual competency levels.
        IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
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