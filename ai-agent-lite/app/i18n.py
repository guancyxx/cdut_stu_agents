"""User-facing string constants — centralized localization module.

All end-user visible text (displayed in the frontend) is defined here.
Chinese strings are written directly (no unicode-escape required).

Internal trace/debug messages also use English strings stored here
for consistency and future i18n support.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDisplayInfo:
    """Display metadata for each agent role — shown in the frontend trace panel."""
    name: str
    description: str


AGENT_DISPLAY: dict[str, AgentDisplayInfo] = {
    "code_reviewer": AgentDisplayInfo(
        name="代码审查专家",
        description="专注于代码质量、效率和风格评估，提供优化建议",
    ),
    "problem_analyzer": AgentDisplayInfo(
        name="问题解析专家",
        description="擅长算法解释和问题拆解，帮助理解题目本质",
    ),
    "contest_coach": AgentDisplayInfo(
        name="竞赛教练",
        description="提供竞赛策略和表现优化建议，提高比赛成绩",
    ),
    "learning_partner": AgentDisplayInfo(
        name="学习伙伴",
        description="提供情感支持和学习动力，陪伴学习旅程",
    ),
    "learning_manager": AgentDisplayInfo(
        name="学习管理专家",
        description="制定个性化学习路径，管理学习进度和效率",
    ),
}

# ── Default suggestions shown after a problem is loaded ────────────────────
# Phrased as what the student would naturally say next (click-to-send).
DEFAULT_SUGGESTIONS = [
    {
        "type": "learn",
        "title": "这道题在考什么？",
        "target": "$problem_title",
        "reason": "先搞懂题目想让你干嘛",
    },
    {
        "type": "practice",
        "title": "给个思路提示",
        "target": "$problem_title",
        "reason": "从一个小提示开始想，比自己硬啃强",
    },
]

# ── Trace stage messages (shown in frontend progress panel) ──────────────────

TRACE = {
    "intent_classification": {
        "title": "意图识别",
        "detail": "正在分析你的问题，确定最佳处理方式...",
    },
    "intent_result": {
        "title": "意图识别完成",
        "detail_routed": "已路由至 {agent} 处理",
    },
    "worker_processing": {
        "title_template": "{agent} 处理中",
        "detail": "正在生成回复...",
    },
    "suggestion_generation": {
        "title": "生成下一步建议",
        "detail": "正在分析知识变化，生成个性化建议...",
    },
    "suggestion_result": {
        "title": "建议生成完成",
        "detail_count": "已生成 {count} 条建议",
    },
    "problem_loaded": {
        "title": "题目已加载",
        "detail": "已加载题目：{title}",
    },
}

# ── Confirmation messages sent to the frontend ─────────────────────────────

def problem_loaded_msg(problem_title: str) -> str:
    """Build the confirmation shown when a problem is loaded."""
    if problem_title:
        return f'好的，题目「{problem_title}」已经加载了，咱们一起看看怎么入手吧～'
    return '题目已加载，有什么不明白的随时问我！'


# ── Error fallback messages (shown to the student) ──────────────────────────

ERROR_FALLBACK = {
    "learning_partner": "我在这儿，随时可以继续。",
    "learning_manager": "暂时无法响应，请稍后再试。",
    "code_reviewer": "代码分析暂时不可用。",
    "problem_analyzer": "问题解析暂时不可用。",
    "contest_coach": "竞赛辅导暂时不可用。",
}