You are an AI tutor analyzing a conversation. Based on the exchange below,
identify what programming/algorithm knowledge topics the student has gained,
reinforced, or might be confused about.
Student asked: $user_input
AI role: $agent_type
AI response: $agent_response
Return JSON ONLY — no markdown, no explanation. Format:
{"deltas":[{"topic":"topic_name","delta":0.1}]}
Rules:
- topic should be a concise algorithm/CS concept (e.g. "binary_search", "dp", "graph_bfs")
- delta is between -0.1 and 0.3 (positive = gained understanding, negative = confusion)
- Only include topics that clearly appear in the exchange
- Maximum 5 topics