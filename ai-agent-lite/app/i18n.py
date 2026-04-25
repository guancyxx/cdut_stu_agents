"""User-facing string constants — centralized localization module.

Code files must NOT contain Chinese characters directly.
All end-user visible text (displayed in the frontend) is defined here,
so the codebase stays English-only while the UI stays in Chinese.

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
        name="\u4ee3\u7801\u5ba1\u67e5\u4e13\u5bb6",
        description="\u4e13\u6ce8\u4e8e\u4ee3\u7801\u8d28\u91cf\u3001\u6548\u7387\u548c\u98ce\u683c\u8bc4\u4f30\uff0c\u63d0\u4f9b\u4f18\u5316\u5efa\u8bae",
    ),
    "problem_analyzer": AgentDisplayInfo(
        name="\u95ee\u9898\u89e3\u6790\u4e13\u5bb6",
        description="\u64c5\u957f\u7b97\u6cd5\u89e3\u91ca\u548c\u95ee\u9898\u62c6\u89e3\uff0c\u5e2e\u52a9\u7406\u89e3\u9898\u76ee\u672c\u8d28",
    ),
    "contest_coach": AgentDisplayInfo(
        name="\u7ade\u8d5b\u6559\u7ec3",
        description="\u63d0\u4f9b\u7ade\u8d5b\u7b56\u7565\u548c\u8868\u73b0\u4f18\u5316\u5efa\u8bae\uff0c\u63d0\u9ad8\u6bd4\u8d5b\u6210\u7ee9",
    ),
    "learning_partner": AgentDisplayInfo(
        name="\u5b66\u4e60\u4f19\u4f34",
        description="\u63d0\u4f9b\u60c5\u611f\u652f\u6301\u548c\u5b66\u4e60\u52a8\u529b\uff0c\u966a\u4f34\u5b66\u4e60\u65c5\u7a0b",
    ),
    "learning_manager": AgentDisplayInfo(
        name="\u5b66\u4e60\u7ba1\u7406\u4e13\u5bb6",
        description="\u5236\u5b9a\u4e2a\u6027\u5316\u5b66\u4e60\u8def\u5f84\uff0c\u7ba1\u7406\u5b66\u4e60\u8fdb\u5ea6\u548c\u6548\u7387",
    ),
}

# ── Default suggestions shown after a problem is loaded ────────────────────
# Phrased as what the student would naturally say next (click-to-send).
DEFAULT_SUGGESTIONS = [
    {
        "type": "learn",
        "title": "\u8fd9\u9053\u9898\u5728\u8003\u4ec0\u4e48\uff1f",
        "target": "$problem_title",
        "reason": "\u5148\u641e\u61c2\u9898\u76ee\u60f3\u8ba9\u4f60\u5e72\u561b",
    },
    {
        "type": "practice",
        "title": "\u7ed9\u4e2a\u601d\u8def\u63d0\u793a",
        "target": "$problem_title",
        "reason": "\u4ece\u4e00\u4e2a\u5c0f\u63d0\u793a\u5f00\u59cb\u60f3\uff0c\u6bd4\u81ea\u5df1\u786c\u5543\u5f3a",
    },
]

# ── Trace stage messages (shown in frontend progress panel) ──────────────────

TRACE = {
    "intent_classification": {
        "title": "\u610f\u56fe\u8bc6\u522b",
        "detail": "\u6b63\u5728\u5206\u6790\u4f60\u7684\u95ee\u9898\uff0c\u786e\u5b9a\u6700\u4f73\u5904\u7406\u65b9\u5f0f...",
    },
    "intent_result": {
        "title": "\u610f\u56fe\u8bc6\u522b\u5b8c\u6210",
        "detail_routed": "\u5df2\u8def\u7531\u81f3 {agent} \u5904\u7406",
    },
    "worker_processing": {
        "title_template": "{agent} \u5904\u7406\u4e2d",
        "detail": "\u6b63\u5728\u751f\u6210\u56de\u590d...",
    },
    "suggestion_generation": {
        "title": "\u751f\u6210\u4e0b\u4e00\u6b65\u5efa\u8bae",
        "detail": "\u6b63\u5728\u5206\u6790\u77e5\u8bc6\u53d8\u5316\uff0c\u751f\u6210\u4e2a\u6027\u5316\u5efa\u8bae...",
    },
    "suggestion_result": {
        "title": "\u5efa\u8bae\u751f\u6210\u5b8c\u6210",
        "detail_count": "\u5df2\u751f\u6210 {count} \u6761\u5efa\u8bae",
    },
    "problem_loaded": {
        "title": "\u9898\u76ee\u5df2\u52a0\u8f7d",
        "detail": "\u5df2\u52a0\u8f7d\u9898\u76ee\uff1a{title}",
    },
}

# ── Confirmation messages sent to the frontend ─────────────────────────────

def problem_loaded_msg(problem_title: str) -> str:
    """Build the confirmation shown when a problem is loaded."""
    if problem_title:
        return f'\u597d\u7684\uff0c\u9898\u76ee\u300c{problem_title}\u300d\u5df2\u7ecf\u52a0\u8f7d\u4e86\uff0c\u54b1\u4eec\u4e00\u8d77\u770b\u770b\u600e\u4e48\u5165\u624b\u5427\uff5e'
    return '\u9898\u76ee\u5df2\u52a0\u8f7d\uff0c\u6709\u4ec0\u4e48\u4e0d\u660e\u767d\u7684\u968f\u65f6\u95ee\u6211\uff01'


# ── Error fallback messages (shown to the student) ──────────────────────────

ERROR_FALLBACK = {
    "learning_partner": "\u6211\u5728\u8fd9\u513f\uff0c\u968f\u65f6\u53ef\u4ee5\u7ee7\u7eed\u3002",
    "learning_manager": "\u6682\u65f6\u65e0\u6cd5\u54cd\u5e94\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002",
    "code_reviewer": "\u4ee3\u7801\u5206\u6790\u6682\u65f6\u4e0d\u53ef\u7528\u3002",
    "problem_analyzer": "\u95ee\u9898\u89e3\u6790\u6682\u65f6\u4e0d\u53ef\u7528\u3002",
    "contest_coach": "\u7ade\u8d5b\u8f85\u5bfc\u6682\u65f6\u4e0d\u53ef\u7528\u3002",
}