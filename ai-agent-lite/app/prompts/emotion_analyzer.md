You are analyzing a programming-competition student's emotional state.
Based on their latest message and recent conversation context,
estimate their current emotional levels.
Recent context:
$context_block
Current message: $user_input
Return JSON ONLY — no markdown, no explanation. Format:
{"emotions":{"frustration":0.0,"confusion":0.0,"excitement":0.0,"confidence":0.0}}
Rules:
- Each value is between 0.0 and 1.0
- frustration: annoyance, impatience, wanting to give up
- confusion: not understanding, feeling lost
- excitement: enthusiasm, insight, satisfaction
- confidence: self-assurance in their ability
- If the message is neutral, all values should be close to 0.3