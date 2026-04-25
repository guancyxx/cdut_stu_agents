"""Knowledge delta computation — pure function comparing before/after knowledge graphs.

Extracted from state_manager.py to follow SRP: state persistence and
knowledge delta calculation are distinct responsibilities.
"""
from typing import Dict, Any


def compute_knowledge_delta(
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare knowledge_graph_position before/after a conversation turn.

    Returns a dict with:
      - gained:    topics newly introduced (mastery > 0 in after but absent/0 in before)
      - improved:  topics where mastery increased (delta > threshold)
      - stable:    topics with no meaningful change
      - weakened:  topics where mastery decreased
      - before_summary: {topic: level} snapshot before
      - after_summary:  {topic: level} snapshot after
    """
    before_kg = before.get("knowledge_graph_position", {}) or {}
    after_kg = after.get("knowledge_graph_position", {}) or {}
    DELTA_THRESHOLD = 0.05

    gained = {}
    improved = {}
    stable = {}
    weakened = {}

    all_topics = set(before_kg.keys()) | set(after_kg.keys())
    for topic in all_topics:
        b_val = before_kg.get(topic, 0.0)
        a_val = after_kg.get(topic, 0.0)
        diff = a_val - b_val

        if b_val == 0 and a_val > 0:
            gained[topic] = round(a_val, 3)
        elif diff > DELTA_THRESHOLD:
            improved[topic] = {"before": round(b_val, 3), "after": round(a_val, 3), "delta": round(diff, 3)}
        elif diff < -DELTA_THRESHOLD:
            weakened[topic] = {"before": round(b_val, 3), "after": round(a_val, 3), "delta": round(diff, 3)}
        else:
            stable[topic] = round(a_val, 3)

    return {
        "gained": gained,
        "improved": improved,
        "stable": stable,
        "weakened": weakened,
        "before_summary": {k: round(v, 3) for k, v in before_kg.items()},
        "after_summary": {k: round(v, 3) for k, v in after_kg.items()},
    }